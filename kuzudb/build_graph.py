import os
import shutil
from pathlib import Path

import kuzu
from codetiming import Timer
from kuzu import Connection

DATA_PATH = Path(__file__).resolve().parents[1] / "data"
NODES_PATH = DATA_PATH / "output" / "nodes"
EDGES_PATH = DATA_PATH / "output" / "edges"


def create_person_node_table(conn: Connection) -> None:
    conn.execute(
        """
        CREATE NODE TABLE
            Person(
                id INT64,
                name STRING,
                gender STRING,
                birthday DATE,
                age INT64,
                isMarried BOOLEAN,
                PRIMARY KEY (id)
            )
        """
    )


def create_city_node_table(conn: Connection) -> None:
    conn.execute(
        """
        CREATE NODE TABLE
            City(
                id INT64,
                city STRING,
                state STRING,
                country STRING,
                lat FLOAT,
                lon FLOAT,
                population INT64,
                PRIMARY KEY (id)
            )
        """
    )


def create_state_node_table(conn: Connection) -> None:
    conn.execute(
        """
        CREATE NODE TABLE
            State(
                id INT64,
                state STRING,
                country STRING,
                PRIMARY KEY (id)
            )
        """
    )


def create_country_node_table(conn: Connection) -> None:
    conn.execute(
        """
        CREATE NODE TABLE
            Country(
                id INT64,
                country STRING,
                PRIMARY KEY (id)
            )
        """
    )


def create_interest_node_table(conn: Connection) -> None:
    conn.execute(
        """
        CREATE NODE TABLE
            Interest(
                id INT64,
                interest STRING,
                PRIMARY KEY (id)
            )
        """
    )


def create_edge_tables(conn: Connection) -> None:
    # Create edge schemas
    conn.execute("CREATE REL TABLE Follows(FROM Person TO Person)")
    conn.execute("CREATE REL TABLE LivesIn(FROM Person TO City)")
    conn.execute("CREATE REL TABLE HasInterest(FROM Person TO Interest)")
    conn.execute("CREATE REL TABLE CityIn(FROM City TO State)")
    conn.execute("CREATE REL TABLE StateIn(FROM State TO Country)")


def main(conn: Connection) -> None:
    with Timer(name="nodes", text="Nodes loaded in {:.4f}s"):
        # Nodes
        create_person_node_table(conn)
        create_city_node_table(conn)
        create_state_node_table(conn)
        create_country_node_table(conn)
        create_interest_node_table(conn)
        conn.execute(f"COPY Person FROM '{NODES_PATH}/persons.parquet';")
        conn.execute(f"COPY City FROM '{NODES_PATH}/cities.parquet';")
        conn.execute(f"COPY State FROM '{NODES_PATH}/states.parquet';")
        conn.execute(f"COPY Country FROM '{NODES_PATH}/countries.parquet';")
        conn.execute(f"COPY Interest FROM '{NODES_PATH}/interests.parquet';")

    with Timer(name="edges", text="Edges loaded in {:.4f}s"):
        # Edges
        create_edge_tables(conn)
        conn.execute(f"COPY Follows FROM '{EDGES_PATH}/follows.parquet';")
        conn.execute(f"COPY LivesIn FROM '{EDGES_PATH}/lives_in.parquet';")
        conn.execute(f"COPY HasInterest FROM '{EDGES_PATH}/interests.parquet';")
        conn.execute(f"COPY CityIn FROM '{EDGES_PATH}/city_in.parquet';")
        conn.execute(f"COPY StateIn FROM '{EDGES_PATH}/state_in.parquet';")

    print(f"Successfully loaded nodes and edges into KùzuDB!")


if __name__ == "__main__":
    DB_NAME = "social_network"
    # Delete directory each time till we have MERGE FROM available in kuzu
    if os.path.exists(DB_NAME):
        shutil.rmtree(DB_NAME)
    # Create database
    db = kuzu.Database(f"./{DB_NAME}")
    CONNECTION = kuzu.Connection(db)

    main(CONNECTION)
