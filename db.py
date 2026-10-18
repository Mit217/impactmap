import os
from dotenv import load_dotenv
from falkordb import FalkorDB

load_dotenv()


def get_db():
    return FalkorDB(
        host=os.getenv("FALKORDB_HOST"),
        port=int(os.getenv("FALKORDB_PORT")),
        username=os.getenv("FALKORDB_USERNAME"),
        password=os.getenv("FALKORDB_PASSWORD"),
    )


def get_graph(name="impactmap"):
    return get_db().select_graph(name)