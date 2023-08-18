import argparse
import os
from pathlib import Path
from typing import Any, Callable, Iterator

import polars as pl
from codetiming import Timer
from dotenv import load_dotenv
from neo4j import GraphDatabase, ManagedTransaction, Session

load_dotenv()

DATA_PATH = Path(__file__).resolve().parents[1] / "data"
NODES_PATH = DATA_PATH / "output" / "nodes"
EDGES_PATH = DATA_PATH / "output" / "edges"
# Config
URI = "bolt://localhost:7687"
NEO4J_USER = os.environ.get("NEO4J_USER")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")

# Custom types
JsonBlob = dict[str, Any]

# --- Nodes ---


def chunk_iterable(iterable: Iterator, chunk_size: int):
  for i in range(0, len(iterable), chunk_size):
    yield iterable[i: i + chunk_size]


def merge_nodes_person(tx: ManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MERGE (p:Person {personID: row.id})
            SET p += row
    """
    tx.run(query, data=data)


def merge_nodes_interests(tx: ManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MERGE (i:Interest {interestID: row.id})
            SET i += row
    """
    tx.run(query, data=data)
    print(f"Created {len(data)} interest nodes")


def merge_nodes_cities(tx: ManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MERGE (ci:City {cityID: row.id})
            SET ci += row
    """
    tx.run(query, data=data)
    print(f"Created {len(data)} city nodes")


def merge_nodes_states(tx: ManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MERGE (s:State {stateID: row.id})
            SET s += row
    """
    tx.run(query, data=data)
    print(f"Created {len(data)} state nodes")


def merge_nodes_countries(tx: ManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MERGE (co:Country {countryID: row.id})
            SET co += row
    """
    tx.run(query, data=data)
    print(f"Created {len(data)} country nodes")


# --- Edges ---

def merge_edges_person(tx: ManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MATCH (p1:Person {personID: row.from})
        MATCH (p2:Person {personID: row.to})
        MERGE (p1)-[:FOLLOWS]->(p2)
    """
    tx.run(query, data=data)


def merge_edges_interests(tx: ManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MATCH (p:Person {personID: row.from})
        MATCH (i:Interest {interestID: row.to})
        MERGE (p)-[:HAS_INTEREST]->(i)
    """
    tx.run(query, data=data)
    print(f"Created {len(data)} person-interest edges")


def merge_edges_lives_in(tx: ManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MATCH (p:Person {personID: row.from})
        MATCH (ci:City {cityID: row.to})
        MERGE (p)-[:LIVES_IN]->(ci)
    """
    tx.run(query, data=data)
    print(f"Created {len(data)} person-city edges")


def merge_edges_city_in(tx: ManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MATCH (ci:City {cityID: row.from})
        MATCH (s:State {stateID: row.to})
        MERGE (ci)-[:CITY_IN]->(s)
    """
    tx.run(query, data=data)
    print(f"Created {len(data)} city-state edges")


def merge_edges_state_in(tx: ManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MATCH (s:State {stateID: row.from})
        MATCH (co:Country {countryID: row.to})
        MERGE (s)-[:STATE_IN]->(co)
    """
    tx.run(query, data=data)
    print(f"Created {len(data)} state-country edges")


# --- Run functions ---


def ingest_person_nodes_in_batches(session: Session, merge_func: Callable) -> None:
    persons = pl.read_parquet(f"{NODES_PATH}/persons.parquet")
    persons_batches = chunk_iterable(persons.to_dicts(), BATCH_SIZE)
    for i, batch in enumerate(persons_batches, 1):
        # Create person nodes
        session.execute_write(merge_func, data=batch)
        print(f"Created {len(batch)} person nodes for batch {i}")


def ingest_person_edges_in_batches(session: Session, merge_func: Callable) -> None:
    """
    Unlike person nodes, edges are just integer pairs, so we can have very large batches
    without running into memory issues when UNWINDing in Cypher.
    """
    follows = pl.read_parquet(f"{EDGES_PATH}/follows.parquet")
    follows_batches = chunk_iterable(follows.to_dicts(), chunk_size=100_000)
    for i, batch in enumerate(follows_batches, 1):
        # Create person-follower edges
        session.execute_write(merge_func, data=batch)
        print(f"Created {len(batch)} person-follower edges for batch {i}")


def create_indexes_and_constraints(session: Session) -> None:
    queries = [
        # constraints
        "CREATE CONSTRAINT personID IF NOT EXISTS FOR (p:Person) REQUIRE p.personID IS UNIQUE ",
        "CREATE CONSTRAINT cityID IF NOT EXISTS FOR (ci:City) REQUIRE ci.cityID IS UNIQUE ",
        "CREATE CONSTRAINT countryID IF NOT EXISTS FOR (co:Country) REQUIRE co.countryID IS UNIQUE ",
        "CREATE CONSTRAINT stateID IF NOT EXISTS FOR (s:State) REQUIRE s.stateID IS UNIQUE ",
        "CREATE CONSTRAINT interestID IF NOT EXISTS FOR (i:Interest) REQUIRE i.interestID IS UNIQUE ",
    ]
    for query in queries:
        session.run(query)


def write_nodes(session: Session) -> None:
    ingest_person_nodes_in_batches(session, merge_nodes_person)
    # Write interest nodes
    interests = pl.read_parquet(f"{NODES_PATH}/interests.parquet")
    session.execute_write(merge_nodes_interests, data=interests.to_dicts())
    # Write city nodes
    cities = pl.read_parquet(f"{NODES_PATH}/cities.parquet")
    session.execute_write(merge_nodes_cities, data=cities.to_dicts())
    # Write state nodes
    states = pl.read_parquet(f"{NODES_PATH}/states.parquet")
    session.execute_write(merge_nodes_states, data=states.to_dicts())
    # Write country nodes
    countries = pl.read_parquet(f"{NODES_PATH}/countries.parquet")
    session.execute_write(merge_nodes_countries, data=countries.to_dicts())


def write_edges(session: Session) -> None:
    ingest_person_edges_in_batches(session, merge_edges_person)
    # Write person-interest edges
    interests = pl.read_parquet(f"{EDGES_PATH}/interests.parquet")
    session.execute_write(merge_edges_interests, data=interests.to_dicts())
    # Write person-city edges
    cities = pl.read_parquet(f"{EDGES_PATH}/lives_in.parquet")
    session.execute_write(merge_edges_lives_in, data=cities.to_dicts())
    # Write city-state edges
    states = pl.read_parquet(f"{EDGES_PATH}/city_in.parquet")
    session.execute_write(merge_edges_city_in, data=states.to_dicts())
    # Write state-country edges
    countries = pl.read_parquet(f"{EDGES_PATH}/state_in.parquet")
    session.execute_write(merge_edges_state_in, data=countries.to_dicts())


def main() -> None:
    with GraphDatabase.driver(URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
        with driver.session(database="neo4j") as session:
            # Create indexes and constraints
            create_indexes_and_constraints(session)
            with Timer(name="nodes", text="Nodes loaded in {:.4f}s"):
                # Write nodes
                write_nodes(session)
            with Timer(name="edges", text="Edges loaded in {:.4f}s"):
                # Write edges after nodes have been created
                write_edges(session)


if __name__ == "__main__":
    # fmt: off
    parser = argparse.ArgumentParser("Build Neo4j graph from files")
    parser.add_argument("--batch_size", "-b", type=int, default=50_000, help="Batch size of nodes to ingest at a time")
    args = parser.parse_args()
    # fmt: on

    BATCH_SIZE = args.batch_size
    main()
