from db import get_db

db = get_db()
graphs = db.list_graphs()
repo_graphs = [g for g in graphs if g.startswith("repo_")]

print("All graphs:", graphs)

if not repo_graphs:
    print("No repo graphs to delete.")
else:
    print("\nRepo graphs:")
    for i, g in enumerate(repo_graphs, 1):
        print(f"  {i}. {g}")

    choice = input("\nNumber to delete, 'all', or blank to cancel: ").strip().lower()

    if choice == "all":
        to_delete = repo_graphs
    elif choice.isdigit() and 1 <= int(choice) <= len(repo_graphs):
        to_delete = [repo_graphs[int(choice) - 1]]
    else:
        to_delete = []

    for g in to_delete:
        db.select_graph(g).delete()
        print("Deleted", g)