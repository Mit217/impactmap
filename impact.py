from db import get_graph


def direct_dependents(name, graph=None):
    """Components that depend directly on `name`."""
    graph = graph or get_graph()
    q = """
    MATCH (a:Component)-[:DEPENDS_ON]->(x:Component {name: $name})
    RETURN a.name
    ORDER BY a.name
    """
    return [r[0] for r in graph.query(q, params={"name": name}).result_set]


def all_dependents(name, graph=None, max_hops=10):
    """Direct and indirect dependents, with the shortest distance (hops)."""
    graph = graph or get_graph()
    q = f"""
    MATCH p = (a:Component)-[:DEPENDS_ON*1..{int(max_hops)}]->(x:Component {{name: $name}})
    RETURN a.name, a.type, min(length(p)) AS hops
    ORDER BY hops, a.name
    """
    return graph.query(q, params={"name": name}).result_set


def dependency_paths(name, graph=None, max_hops=10, limit=100):
    """Paths from affected components down to `name` (capped at `limit`)."""
    graph = graph or get_graph()
    q = f"""
    MATCH p = (a:Component)-[:DEPENDS_ON*1..{int(max_hops)}]->(x:Component {{name: $name}})
    RETURN [n IN nodes(p) | n.name] AS path, length(p) AS hops
    ORDER BY hops
    LIMIT {int(limit)}
    """
    return [r[0] for r in graph.query(q, params={"name": name}).result_set]

def dependents_with_location(name, graph=None, max_hops=10):
    """Affected components with their file path (repo graphs) and distance."""
    graph = graph or get_graph()
    q = f"""
    MATCH p = (a:Component)-[:DEPENDS_ON*1..{int(max_hops)}]->(x:Component {{name: $name}})
    RETURN a.name, a.type, a.description, min(length(p)) AS hops
    ORDER BY hops, a.name
    """
    return graph.query(q, params={"name": name}).result_set


def direct_import_sites(name, graph=None):
    """For each direct dependent: (name, file, line where it imports `name`)."""
    graph = graph or get_graph()
    q = """
    MATCH (a:Component)-[r:DEPENDS_ON]->(x:Component {name: $name})
    RETURN a.name, a.description, r.line ORDER BY a.name
    """
    return graph.query(q, params={"name": name}).result_set

if __name__ == "__main__":
    for failed in ["Auth Service", "User Database", "Payment Service"]:
        print(f"\n=== If '{failed}' fails ===")
        print("Direct:", direct_dependents(failed))
        for name, ctype, hops in all_dependents(failed):
            print(f"  {name} ({ctype}) - {hops} hop(s) away")