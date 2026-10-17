import os
from dotenv import load_dotenv
from falkordb import FalkorDB

load_dotenv()  # reads the .env file


def get_graph():
    db = FalkorDB(
        host=os.getenv("FALKORDB_HOST"),
        port=int(os.getenv("FALKORDB_PORT")),
        username=os.getenv("FALKORDB_USERNAME"),
        password=os.getenv("FALKORDB_PASSWORD"),
    )
    return db.select_graph("impactmap")