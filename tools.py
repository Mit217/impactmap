from impact import direct_dependents, all_dependents, dependency_paths
import difflib

def _exists(graph, name):
    q = "MATCH (c:Component {name: $name}) RETURN count(c)"
    return graph.query(q, params={"name": name}).result_set[0][0] > 0

def similar_names(graph, name, n=5):
    """Closest component names to a mistyped one."""
    names = [r[0] for r in graph.query("MATCH (c:Component) RETURN c.name").result_set]
    close = difflib.get_close_matches(name, names, n=n, cutoff=0.5)
    low = name.lower()
    close += [x for x in names if low in x.lower() and x not in close]
    return close[:n]

def find_component(graph, query, limit=15):
    """Search component names (case-insensitive substring match)."""
    q = """
    MATCH (c:Component)
    WHERE toLower(c.name) CONTAINS toLower($q)
    RETURN c.name, c.type ORDER BY c.name LIMIT $limit
    """
    rows = graph.query(q, params={"q": query, "limit": int(limit)}).result_set
    return [{"name": n, "type": t} for n, t in rows]


def dependencies_of(graph, name, max_hops=3):
    """What `name` itself relies on (outgoing edges)."""
    q = f"""
    MATCH p = (x:Component {{name: $name}})-[:DEPENDS_ON*1..{int(max_hops)}]->(b:Component)
    RETURN b.name, b.type, min(length(p)) AS hops
    ORDER BY hops, b.name LIMIT 40
    """
    rows = graph.query(q, params={"name": name}).result_set
    return [{"name": n, "type": t, "hops": h} for n, t, h in rows]


def most_depended_on(graph, limit=10):
    q = """
    MATCH (a:Component)-[:DEPENDS_ON]->(b:Component)
    RETURN b.name, count(a) AS n ORDER BY n DESC LIMIT $limit
    """
    rows = graph.query(q, params={"limit": int(limit)}).result_set
    return [{"name": n, "direct_dependents": c} for n, c in rows]


# ---- Tool definitions the LLM will see -------------------------------

NAME_PROP = {"name": {"type": "string", "description": "Exact component name"}}

TOOL_SPECS = [
    {
        "name": "find_component",
        "description": "Search component names by substring. Use this first when "
                       "the user's wording may not match an exact name.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "get_direct_dependents",
        "description": "Components that directly depend on the given component.",
        "input_schema": {"type": "object", "properties": NAME_PROP, "required": ["name"]},
    },
    {
        "name": "get_all_affected",
        "description": "All components directly or indirectly affected if the given "
                       "component fails or changes, with distance in hops.",
        "input_schema": {"type": "object", "properties": NAME_PROP, "required": ["name"]},
    },
    {
        "name": "get_dependency_paths",
        "description": "Example dependency chains explaining WHY components are "
                       "affected. Each path reads 'depends on' left to right.",
        "input_schema": {"type": "object", "properties": NAME_PROP, "required": ["name"]},
    },
    {
        "name": "get_dependencies_of",
        "description": "What the given component itself depends on (its upstream "
                       "risks), up to 3 hops.",
        "input_schema": {"type": "object", "properties": NAME_PROP, "required": ["name"]},
    },
    {
        "name": "get_most_depended_on",
        "description": "The most critical components, ranked by direct dependents.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def run_tool(graph, tool_name, args):
    """Run one tool and return a JSON-friendly result. Never raises."""
    try:
        if tool_name == "find_component":
            return find_component(graph, args["query"])
        if tool_name == "get_most_depended_on":
            return most_depended_on(graph)

        name = args["name"]
        if not _exists(graph, name):
            return {
                "error": f"No component named '{name}'.",
                "suggestions": similar_names(graph, name),
            }

        if tool_name == "get_direct_dependents":
            return direct_dependents(name, graph=graph)
        if tool_name == "get_all_affected":
            rows = all_dependents(name, graph=graph)
            return {
                "total": len(rows),
                "affected": [
                    {"name": n, "type": t, "hops": h} for n, t, h in rows[:60]
                ],
            }
        if tool_name == "get_dependency_paths":
            return dependency_paths(name, graph=graph, limit=15)
        if tool_name == "get_dependencies_of":
            return dependencies_of(graph, name)
        return {"error": f"Unknown tool {tool_name}"}
    except Exception as e:
        return {"error": str(e)}