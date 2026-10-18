import streamlit as st
from db import get_graph
from impact import direct_dependents, all_dependents, dependency_paths
from repo_graph import load_repo_graph
from agent import ask_agent

st.set_page_config(page_title="ImpactMap", page_icon="🗺️")
st.title("ImpactMap")
st.write("Select a component to see what could be affected if it fails or changes.")


@st.cache_data(show_spinner=False)
def list_components(graph_name):
    g = get_graph(graph_name)
    rows = g.query("MATCH (c:Component) RETURN c.name ORDER BY c.name").result_set
    return [r[0] for r in rows]


mode = st.radio(
    "Data source",
    ["Sample architecture", "GitHub repo (Python)"],
    horizontal=True,
)

if mode == "Sample architecture":
    graph_name = "impactmap"
else:
    url = st.text_input("Public GitHub repo URL", placeholder="https://github.com/owner/repo")
    if st.button("Load repo") and url:
        try:
            with st.spinner("Downloading and building the dependency graph..."):
                _, name, n_mod, n_dep = load_repo_graph(url)
            list_components.clear()
            st.session_state["repo_graph"] = name
            st.session_state["repo_stats"] = (n_mod, n_dep)
        except Exception as e:
            st.error(f"Could not load that repo: {e}")

    graph_name = st.session_state.get("repo_graph")
    if graph_name:
        n_mod, n_dep = st.session_state["repo_stats"]
        st.success(f"Loaded {n_mod} modules and {n_dep} dependencies.")
    else:
        st.info("Enter a repo URL and click **Load repo**.")
        st.stop()

graph = get_graph(graph_name)

top = graph.query(
    "MATCH (a:Component)-[:DEPENDS_ON]->(b:Component) "
    "RETURN b.name, count(a) AS n ORDER BY n DESC LIMIT 10"
).result_set
if top:
    with st.expander("Most depended-on components (good ones to try)"):
        st.dataframe(
            [{"Component": m, "Direct dependents": n} for m, n in top]
        )

components = list_components(graph_name)
failed = st.selectbox("Which component fails or changes?", components)

if st.button("Analyze impact"):
    direct = direct_dependents(failed, graph=graph)
    affected = all_dependents(failed, graph=graph)

    if not affected:
        st.success(f"Nothing in the graph depends on {failed}.")
    else:
        c1, c2 = st.columns(2)
        c1.metric("Directly affected", len(direct))
        c2.metric("Total potentially affected", len(affected))

        st.subheader("Affected components")
        st.dataframe(
            [
                {"Component": n, "Type": t, "Distance (hops)": h}
                for n, t, h in affected
            ]
        )

        with st.expander("Dependency paths (up to 100)"):
            st.caption("Read each arrow as 'depends on'.")
            for path in dependency_paths(failed, graph=graph):
                st.write(" → ".join(path))

    st.caption(
        "These results are static-import estimates, "
        "not proof that every listed component will break."
    )
st.divider()
st.subheader("Ask the agent")
st.caption(
    "The agent picks graph queries as tools, runs them on FalkorDB, "
    "and explains what the graph returned."
)

question = st.text_input(
    "Your question",
    placeholder="I'm about to change the Auth Service. What should I review first?",
    key="agent_question",
)

if st.button("Ask") and question:
    with st.spinner("Agent is querying the graph... (free-tier limits may add a short wait)"):
        answer, trace = ask_agent(question, graph)

    st.markdown(answer)

    with st.expander(f"Graph queries the agent ran ({len(trace)})", expanded=True):
        for t in trace:
            st.code(f"{t['tool']}({t['input']})", language="python")