from db import get_graph

graph = get_graph()

# Start clean so you can re-run this file safely
graph.query("MATCH (n) DETACH DELETE n")

components = [
    ("Dashboard", "Frontend", "Web dashboard used by staff"),
    ("Mobile App", "Frontend", "Customer mobile application"),
    ("API Gateway", "Gateway", "Single entry point for all API requests"),
    ("Auth Service", "Service", "Handles login and tokens"),
    ("Order Service", "Service", "Creates and manages orders"),
    ("Payment Service", "Service", "Processes payments"),
    ("Notification Service", "Service", "Sends emails and alerts"),
    ("Reporting Service", "Service", "Generates reports and analytics"),
    ("User Database", "Database", "Stores user accounts"),
    ("Order Database", "Database", "Stores orders"),
    ("Cache", "Cache", "In-memory cache for sessions"),
]

# (A, B) means: A DEPENDS_ON B
dependencies = [
    ("Dashboard", "API Gateway"),
    ("Dashboard", "Reporting Service"),
    ("Mobile App", "API Gateway"),
    ("API Gateway", "Auth Service"),
    ("API Gateway", "Order Service"),
    ("Auth Service", "User Database"),
    ("Auth Service", "Cache"),
    ("Order Service", "Order Database"),
    ("Order Service", "Payment Service"),
    ("Order Service", "Notification Service"),
    ("Notification Service", "User Database"),
    ("Reporting Service", "User Database"),
]

for name, ctype, desc in components:
    graph.query(
        "CREATE (:Component {name: $name, type: $type, description: $desc})",
        params={"name": name, "type": ctype, "desc": desc},
    )

for a, b in dependencies:
    graph.query(
        "MATCH (a:Component {name: $a}), (b:Component {name: $b}) "
        "CREATE (a)-[:DEPENDS_ON]->(b)",
        params={"a": a, "b": b},
    )

# Verify what was stored
nodes = graph.query("MATCH (c:Component) RETURN count(c)").result_set[0][0]
edges = graph.query("MATCH ()-[r:DEPENDS_ON]->() RETURN count(r)").result_set[0][0]
print(f"Loaded {nodes} components and {edges} dependencies")

for row in graph.query(
    "MATCH (a:Component)-[:DEPENDS_ON]->(b:Component) RETURN a.name, b.name"
).result_set:
    print(f"{row[0]}  -->  {row[1]}")