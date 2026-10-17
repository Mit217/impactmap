# ImpactMap

A dependency-impact analysis tool built with FalkorDB. Select a software
component and see which other components could be affected if it fails,
directly or indirectly.

## Problem
In systems with many connected components (APIs, services, databases,
frontends), tracing what depends on what by hand is slow and error-prone.

## How it works
- Components are stored as **nodes**; dependencies as `DEPENDS_ON` **edges**.
  `(A)-[:DEPENDS_ON]->(B)` means "A depends on B".
- If B fails, ImpactMap uses a Cypher variable-length traversal to find every
  component with a path to B:
  `MATCH p = (a)-[:DEPENDS_ON*1..10]->(x {name: $name})`
- Results (affected components, distance, and paths) come directly from
  FalkorDB graph queries.
- Direction is respected: if Auth Service fails, User Database is not marked
  as affected, because Auth Service depends on it, not the other way around.

## Tech stack
Python, FalkorDB, Cypher, Streamlit

## Setup
1. Clone the repo and create a virtual environment:
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
2. Get a FalkorDB instance (FalkorDB Cloud free tier, or locally with Docker).
3. Copy `.env.example` to `.env` and fill in your connection details.
4. Load the sample graph: `python load_graph.py`
5. Run the app: `streamlit run app.py`

## Sample architecture
[11 components, 12 dependencies: Dashboard, Mobile App, API Gateway,
Auth Service, Order Service, Payment Service, Notification Service,
Reporting Service, User Database, Order Database, Cache]

## Screenshots
[add images here]

## Limitations
- Uses a predefined sample graph, not live repository data.
- Results are dependency-based estimates, not proof of real failures.

## Future work
- AI-generated explanations of results
- Importing real dependency data from repositories