from db import get_graph

graph = get_graph()


def direct_dependents(name):
    """Components that depend directly on `name`."""
    q = """
    MATCH (a:Component)-[:DEPENDS_ON]->(x:Component {name: $name})
    RETURN a.name
    ORDER BY a.name
    """
    return [r[0] for r in graph.query(q, params={"name": name}).result_set]


def all_dependents(name):
    """Direct and indirect dependents, with the shortest distance (hops)."""
    q = """
    MATCH p = (a:Component)-[:DEPENDS_ON*1..10]->(x:Component {name: $name})
    RETURN a.name, a.type, min(length(p)) AS hops
    ORDER BY hops, a.name
    """
    return graph.query(q, params={"name": name}).result_set


def dependency_paths(name):
    """Every path from an affected component down to `name`."""
    q = """
    MATCH p = (a:Component)-[:DEPENDS_ON*1..10]->(x:Component {name: $name})
    RETURN [n IN nodes(p) | n.name] AS path, length(p) AS hops
    ORDER BY hops
    """
    return [r[0] for r in graph.query(q, params={"name": name}).result_set]

if __name__ == "__main__":
    for failed in ["Auth Service", "User Database", "Payment Service"]:
        print(f"\n=== If '{failed}' fails ===")

        print("Direct:", direct_dependents(failed))

        print("All affected:")
        for name, ctype, hops in all_dependents(failed):
            print(f"  {name} ({ctype}) - {hops} hop(s) away")

        print("Paths:")
        for path in dependency_paths(failed):
            print("  " + "  -->  ".join(path))