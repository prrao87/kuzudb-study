import argparse
import asyncio
import os
from pathlib import Path
from typing import Any, Callable, Iterator

import polars as pl
from codetiming import Timer
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase, AsyncManagedTransaction, AsyncSession

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


def chunk_iterable(iterable: Iterator, chunk_size: int):
    for i in range(0, len(iterable), chunk_size):
        yield iterable[i : i + chunk_size]


# --- Nodes ---

async def merge_nodes_person(tx: AsyncManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MERGE (p:Person {personID: row.id})
            SET p += row
    """
    await tx.run(query, data=data)


async def merge_nodes_interests(tx: AsyncManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MERGE (i:Interest {interestID: row.id})
            SET i += row
    """
    await tx.run(query, data=data)
    print(f"Created {len(data)} interest nodes")


async def merge_nodes_cities(tx: AsyncManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MERGE (ci:City {cityID: row.id})
            SET ci += row
    """
    await tx.run(query, data=data)
    print(f"Created {len(data)} city nodes")


async def merge_nodes_states(tx: AsyncManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MERGE (s:State {stateID: row.id})
            SET s += row
    """
    await tx.run(query, data=data)
    print(f"Created {len(data)} state nodes")


async def merge_nodes_countries(tx: AsyncManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MERGE (co:Country {countryID: row.id})
            SET co += row
    """
    await tx.run(query, data=data)
    print(f"Created {len(data)} country nodes")


# --- Edges ---


async def merge_edges_person(tx: AsyncManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MATCH (p1:Person {personID: row.from})
        MATCH (p2:Person {personID: row.to})
        MERGE (p1)-[:FOLLOWS]->(p2)
    """
    await tx.run(query, data=data)


async def merge_edges_interested_in(tx: AsyncManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MATCH (p:Person {personID: row.from})
        MATCH (i:Interest {interestID: row.to})
        MERGE (p)-[:HAS_INTEREST]->(i)
    """
    await tx.run(query, data=data)
    print(f"Created {len(data)} person-interest edges")


async def merge_edges_lives_in(tx: AsyncManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MATCH (p:Person {personID: row.from})
        MATCH (ci:City {cityID: row.to})
        MERGE (p)-[:LIVES_IN]->(ci)
    """
    await tx.run(query, data=data)
    print(f"Created {len(data)} person-city edges")


async def merge_edges_city_in(tx: AsyncManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MATCH (ci:City {cityID: row.from})
        MATCH (s:State {stateID: row.to})
        MERGE (ci)-[:CITY_IN]->(s)
    """
    await tx.run(query, data=data)
    print(f"Created {len(data)} city-state edges")


async def merge_edges_state_in(tx: AsyncManagedTransaction, data: list[JsonBlob]) -> None:
    query = """
        UNWIND $data AS row
        MATCH (s:State {stateID: row.from})
        MATCH (co:Country {countryID: row.to})
        MERGE (s)-[:STATE_IN]->(co)
    """
    await tx.run(query, data=data)
    print(f"Created {len(data)} state-country edges")


# --- Run functions ---


async def ingest_person_nodes_in_batches(session: AsyncSession, merge_func: Callable) -> None:
    persons = pl.read_parquet(f"{NODES_PATH}/persons.parquet")
    persons_batches = chunk_iterable(persons.to_dicts(), BATCH_SIZE)
    for i, batch in enumerate(persons_batches, 1):
        # Create person nodes
        await session.execute_write(merge_func, data=batch)
        print(f"Created {len(batch)} person nodes for batch {i}")


async def ingest_person_edges_in_batches(session: AsyncSession, merge_func: Callable) -> None:
    """
    Unlike person nodes, edges are just integer pairs, so we can have very large batches
    without running into memory issues when UNWINDing in Cypher.
    """
    follows = pl.read_parquet(f"{EDGES_PATH}/follows.parquet")
    follows_batches = chunk_iterable(follows.to_dicts(), chunk_size=BATCH_SIZE)
    for i, batch in enumerate(follows_batches, 1):
        # Create person-follower edges
        await session.execute_write(merge_func, data=batch)
        print(f"Created {len(batch)} person-follower edges for batch {i}")


async def create_indexes_and_constraints(session: AsyncSession) -> None:
    queries = [
        # constraints
        "CREATE CONSTRAINT personID IF NOT EXISTS FOR (p:Person) REQUIRE p.personID IS UNIQUE ",
        "CREATE CONSTRAINT cityID IF NOT EXISTS FOR (ci:City) REQUIRE ci.cityID IS UNIQUE ",
        "CREATE CONSTRAINT countryID IF NOT EXISTS FOR (co:Country) REQUIRE co.countryID IS UNIQUE ",
        "CREATE CONSTRAINT stateID IF NOT EXISTS FOR (s:State) REQUIRE s.stateID IS UNIQUE ",
        "CREATE CONSTRAINT interestID IF NOT EXISTS FOR (i:Interest) REQUIRE i.interestID IS UNIQUE ",
    ]
    for query in queries:
        await session.run(query)


async def write_nodes(session: AsyncSession) -> None:
    await ingest_person_nodes_in_batches(session, merge_nodes_person)
    # Write interest nodes
    interests = pl.read_parquet(f"{NODES_PATH}/interests.parquet")
    await session.execute_write(merge_nodes_interests, data=interests.to_dicts())
    # Write city nodes
    cities = pl.read_parquet(f"{NODES_PATH}/cities.parquet")
    await session.execute_write(merge_nodes_cities, data=cities.to_dicts())
    # Write state nodes
    states = pl.read_parquet(f"{NODES_PATH}/states.parquet")
    await session.execute_write(merge_nodes_states, data=states.to_dicts())
    # Write country nodes
    countries = pl.read_parquet(f"{NODES_PATH}/countries.parquet")
    await session.execute_write(merge_nodes_countries, data=countries.to_dicts())


async def write_edges(session: AsyncSession) -> None:
    await ingest_person_edges_in_batches(session, merge_edges_person)
    # Write person-interest edges
    interests = pl.read_parquet(f"{EDGES_PATH}/interested_in.parquet")
    await session.execute_write(merge_edges_interested_in, data=interests.to_dicts())
    # Write person-city edges
    cities = pl.read_parquet(f"{EDGES_PATH}/lives_in.parquet")
    await session.execute_write(merge_edges_lives_in, data=cities.to_dicts())
    # Write city-state edges
    states = pl.read_parquet(f"{EDGES_PATH}/city_in.parquet")
    await session.execute_write(merge_edges_city_in, data=states.to_dicts())
    # Write state-country edges
    countries = pl.read_parquet(f"{EDGES_PATH}/state_in.parquet")
    await session.execute_write(merge_edges_state_in, data=countries.to_dicts())


async def main() -> None:
    async with AsyncGraphDatabase.driver(URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
        async with driver.session(database="neo4j") as session:
            # Create indexes and constraints
            await create_indexes_and_constraints(session)
            with Timer(name="nodes", text="Nodes loaded in {:.4f}s"):
                # Write nodes
                await write_nodes(session)
            with Timer(name="edges", text="Edges loaded in {:.4f}s"):
                # Write edges after nodes have been created
                await write_edges(session)


if __name__ == "__main__":
    # fmt: off
    parser = argparse.ArgumentParser("Build Neo4j graph from files")
    parser.add_argument("--batch_size", "-b", type=int, default=500_000, help="Batch size of nodes to ingest at a time")
    args = parser.parse_args()
    # fmt: on

    BATCH_SIZE = args.batch_size
    asyncio.run(main())
