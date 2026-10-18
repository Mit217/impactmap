from db import get_graph
from tools import run_tool

g = get_graph()  # sample graph

print(run_tool(g, "find_component", {"query": "auth"}))
print(run_tool(g, "get_all_affected", {"name": "Auth Service"}))
print(run_tool(g, "get_dependencies_of", {"name": "Order Service"}))
print(run_tool(g, "get_most_depended_on", {}))
print(run_tool(g, "get_all_affected", {"name": "Auth Servce"}))  # typo on purpose