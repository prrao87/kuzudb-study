import argparse
import os
from pathlib import Path
from typing import Any, Callable

import polars as pl
from codetiming import Timer
from dotenv import load_dotenv
from neo4j import GraphDatabase, ManagedTransaction, Session
from polars.io.csv.batched_reader import BatchedCsvReader

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


def read_nodes_person(batch_size: int) -> BatchedCsvReader:
    """Process person nodes CSV file in batches"""
    csv_reader = pl.read_csv_batched(
        f"{NODES_PATH}/persons.csv", separator="|", try_parse_dates=True, batch_size=batch_size
    )
    return csv_reader


def merge_nodes_person(tx: ManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MERGE (p:Person {personID: row.id})
            SET p += row
    """
    tx.run(query, data=data)
    print(f"Created {len(data)} person nodes")


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


def read_edges_person(batch_size: int) -> None:
    csv_reader = pl.read_csv_batched(
        f"{EDGES_PATH}/follows.csv", separator="|", batch_size=batch_size
    )
    return csv_reader


def read_edges_interests(batch_size: int) -> None:
    csv_reader = pl.read_csv_batched(
        f"{EDGES_PATH}/interests.csv", separator="|", batch_size=batch_size
    )
    return csv_reader


def read_edges_lives_in(batch_size: int) -> None:
    csv_reader = pl.read_csv_batched(
        f"{EDGES_PATH}/lives_in.csv", separator="|", batch_size=batch_size
    )
    return csv_reader


def read_edges_city_in(batch_size: int) -> None:
    csv_reader = pl.read_csv_batched(
        f"{EDGES_PATH}/city_in.csv", separator="|", batch_size=batch_size
    )
    return csv_reader


def read_edges_state_in(batch_size: int) -> None:
    csv_reader = pl.read_csv_batched(
        f"{EDGES_PATH}/state_in.csv", separator="|", batch_size=batch_size
    )
    return csv_reader


def merge_edges_person(tx: ManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MATCH (p1:Person {personID: row.from})
        MATCH (p2:Person {personID: row.to})
        MERGE (p1)-[:FOLLOWS]->(p2)
    """
    tx.run(query, data=data)
    print(f"Created {len(data)} person-follower edges")


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


def ingest_in_batches(session: Session, read_func: Callable, merge_func: Callable) -> None:
    reader = read_func(batch_size=BATCH_SIZE)
    batches = reader.next_batches(BATCH_SIZE)
    for i, batch in enumerate(batches):
        # Convert DataFrame to a list of dictionaries
        data = batch.to_dicts()
        # Create person nodes
        session.execute_write(merge_func, data=data)


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
    # Write person nodes in batches
    ingest_in_batches(session, read_nodes_person, merge_nodes_person)
    # Write interest nodes
    interests = pl.read_csv(f"{NODES_PATH}/interests.csv", separator="|")
    session.execute_write(merge_nodes_interests, data=interests.to_dicts())
    # Write city nodes
    cities = pl.read_csv(f"{NODES_PATH}/cities.csv", separator="|")
    session.execute_write(merge_nodes_cities, data=cities.to_dicts())
    # Write state nodes
    states = pl.read_csv(f"{NODES_PATH}/states.csv", separator="|")
    session.execute_write(merge_nodes_states, data=states.to_dicts())
    # Write country nodes
    countries = pl.read_csv(f"{NODES_PATH}/countries.csv", separator="|")
    session.execute_write(merge_nodes_countries, data=countries.to_dicts())


def write_edges(session: Session) -> None:
    ingest_in_batches(session, read_edges_person, merge_edges_person)
    ingest_in_batches(session, read_edges_interests, merge_edges_interests)
    ingest_in_batches(session, read_edges_lives_in, merge_edges_lives_in)
    ingest_in_batches(session, read_edges_city_in, merge_edges_city_in)
    ingest_in_batches(session, read_edges_state_in, merge_edges_state_in)


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
    parser = argparse.ArgumentParser("Build Neo4j graph from files")
    parser.add_argument(
        "--batch_size", "-b", type=int, default=50_000, help="Batch size of CSV reader"
    )
    args = parser.parse_args()

    BATCH_SIZE = args.batch_size
    main()
