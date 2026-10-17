import streamlit as st
from db import get_graph
from impact import direct_dependents, all_dependents, dependency_paths

st.set_page_config(page_title="ImpactMap", page_icon="🗺️")

st.title("ImpactMap")
st.write("Select a component to see what could be affected if it fails.")


@st.cache_data
def load_components():
    graph = get_graph()
    rows = graph.query(
        "MATCH (c:Component) RETURN c.name ORDER BY c.name"
    ).result_set
    return [r[0] for r in rows]


components = load_components()
failed = st.selectbox("Which component fails?", components)

if st.button("Analyze impact"):
    direct = direct_dependents(failed)
    affected = all_dependents(failed)
    paths = dependency_paths(failed)

    if not affected:
        st.success(f"Nothing in the graph depends on {failed}.")
    else:
        col1, col2 = st.columns(2)
        col1.metric("Directly affected", len(direct))
        col2.metric("Total potentially affected", len(affected))

        st.subheader("Affected components")
        st.dataframe(
            [
                {"Component": name, "Type": ctype, "Distance (hops)": hops}
                for name, ctype, hops in affected
            ]
        )

        st.subheader("Dependency paths")
        st.caption("Read each arrow as 'depends on'.")
        for path in paths:
            st.write(" → ".join(path))

    st.caption(
        "These results are dependency-based estimates, "
        "not proof that every listed component will fail."
    )