import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from db import get_graph
from tools import TOOL_SPECS, run_tool

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

SYSTEM = """You are ImpactMap, an assistant that analyzes software dependency graphs.
In this graph, (A)-[:DEPENDS_ON]->(B) means A depends on B. If B fails or changes,
the components that depend on B (directly or indirectly) are the ones affected.

Rules:
- Use the tools for every fact. Never guess which components are affected.
- If a tool returns an error with suggestions, retry with the closest suggested name.
- Use get_all_affected for scope, get_dependency_paths to explain why, and
  get_dependencies_of when the user asks what a component relies on.
- Components at 1 hop are most at risk; farther ones are indirect.
- Answer concisely: a short summary, then a prioritized review checklist
  (what to check first and why, citing the dependency path).
- State that results are static dependency estimates, not proof of failure.
- Call several tools at once when you can (for example get_all_affected and
  get_dependency_paths together) to keep the number of steps small.
- Call find_component only if the user's wording may not match a component name,
  and at most once.
- For "where is X defined" questions, use find_symbol and report the file and line.
- When results include "file" and "imports_it_at_line", show them for each component
  as file:line, so the user knows where to look."""

def _declarations():
    """Convert our tool specs into Gemini function declarations."""
    decls = []
    for spec in TOOL_SPECS:
        schema = spec["input_schema"]
        kwargs = {"name": spec["name"], "description": spec["description"]}
        if schema.get("properties"):  # tools with no arguments omit parameters
            kwargs["parameters_json_schema"] = schema
        decls.append(types.FunctionDeclaration(**kwargs))
    return decls


CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM,
    tools=[types.Tool(function_declarations=_declarations())],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
)

def _generate(contents):
    """Call the model, waiting and retrying if the free-tier rate limit is hit."""
    for attempt in range(3):
        try:
            return client.models.generate_content(
                model=MODEL, contents=contents, config=CONFIG
            )
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                m = re.search(r"retry in ([\d.]+)s", msg)
                wait = float(m.group(1)) + 1 if m else 30
                if attempt < 2 and wait <= 90:
                    time.sleep(wait)
                    continue
            raise

def ask_agent(question, graph, max_steps=8):
    """Returns (answer_text, trace). trace lists every graph tool call made."""
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=question)])]
    trace = []

    for _ in range(max_steps):
        try:
            resp = _generate(contents)
        except Exception as e:
            return f"The model call failed: {e}", trace

        if not resp.candidates or not resp.candidates[0].content:
            return "The model returned no answer.", trace
        content = resp.candidates[0].content
        parts = content.parts or []
        contents.append(content)

        calls = [p.function_call for p in parts if p.function_call]
        if not calls:
            return "".join(p.text for p in parts if p.text), trace

        reply_parts = []
        for fc in calls:
            args = dict(fc.args or {})
            out = run_tool(graph, fc.name, args)
            trace.append({"tool": fc.name, "input": args, "output": out})
            reply_parts.append(
                types.Part.from_function_response(
                    name=fc.name, response={"result": out}
                )
            )
        contents.append(types.Content(role="user", parts=reply_parts))

    return "Stopped: the agent used too many steps.", trace


if __name__ == "__main__":
    graph = get_graph()  # sample graph
    while True:
        q = input("\nAsk ImpactMap (blank to quit): ").strip()
        if not q:
            break
        answer, trace = ask_agent(q, graph)
        print("\nGraph tools used:")
        for t in trace:
            print(f"  {t['tool']}({t['input']})")
        print("\n" + answer)