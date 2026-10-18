import re

from db import get_db
from repo_loader import (
    parse_repo_url,
    download_repo,
    read_python_files,
    build_dependencies,
)


def graph_name_for(owner, repo):
    return re.sub(r"[^a-z0-9_]", "_", f"repo_{owner}_{repo}".lower())


def load_repo_graph(url):
    """Download a public repo, build its import graph in FalkorDB.
    Returns (graph, graph_name, n_modules, n_deps)."""
    owner, repo = parse_repo_url(url)
    files = read_python_files(download_repo(owner, repo))
    if not files:
        raise ValueError("No Python files found in this repo.")
    modules, deps = build_dependencies(files)

    name = graph_name_for(owner, repo)
    graph = get_db().select_graph(name)

    try:
        graph.delete()  # replace any earlier analysis of this repo
    except Exception:
        pass  # graph didn't exist yet
    graph = get_db().select_graph(name)

    rows = [
        {
            "name": mod,
            "type": "Package" if path.endswith("__init__.py") else "Module",
            "path": path,
        }
        for mod, path in modules.items()
    ]
    graph.query(
        "UNWIND $rows AS row "
        "CREATE (:Component {name: row.name, type: row.type, description: row.path})",
        params={"rows": rows},
    )
    graph.query("CREATE INDEX FOR (c:Component) ON (c.name)")

    pairs = [{"a": a, "b": b} for a, b in sorted(deps)]
    for i in range(0, len(pairs), 500):
        graph.query(
            "UNWIND $pairs AS p "
            "MATCH (a:Component {name: p.a}), (b:Component {name: p.b}) "
            "CREATE (a)-[:DEPENDS_ON]->(b)",
            params={"pairs": pairs[i : i + 500]},
        )

    return graph, name, len(rows), len(pairs)


if __name__ == "__main__":
    from impact import all_dependents, direct_dependents

    url = input("GitHub repo URL: ")
    graph, name, n_mod, n_dep = load_repo_graph(url)
    print(f"\nGraph '{name}': {n_mod} modules, {n_dep} dependencies")
    top = graph.query(
        "MATCH (a:Component)-[:DEPENDS_ON]->(b:Component) "
        "RETURN b.name, count(a) AS n ORDER BY n DESC LIMIT 10"
    ).result_set
    print("\nMost depended-on modules (good ones to analyze):")
    for mod, n in top:
        print(f"  {mod}  ({n} direct dependents)")

    while True:
        failed = input("\nModule to analyze (blank to quit): ").strip()
        if not failed:
            break
        affected = all_dependents(failed, graph=graph)
        if not affected:
            print("Nothing depends on it (or the name doesn't exist).")
            continue
        print("Direct:", direct_dependents(failed, graph=graph))
        for n, t, hops in affected:
            print(f"  {n} ({t}) - {hops} hop(s) away")
            
            