"""
Generate edges between persons and their followers (who are also persons in the same graph).

The aim is to scale up the generation of edges based on the number of nodes in the graph,
while also keeping edges between nodes in a way that's not a uniform distribution.
In the real world, some people are way more connected than others.
"""
import argparse
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl


def select_random_ids(df: pl.DataFrame, num: int) -> list[int]:
    """Select random IDs from a column of a dataframe"""
    connections = list(np.random.choice(df["id"], size=num, replace=False))
    return connections


def get_persons_df(filepath: Path) -> pl.DataFrame:
    # Read in person data
    persons_df = pl.read_csv(filepath, separator="|").with_columns(
        pl.col("birthday").str.strptime(pl.Date, "%Y-%m-%d")
    )
    return persons_df


def get_initial_person_edges(persons_df: pl.DataFrame) -> pl.DataFrame:
    """
    Produce an initial list of person-person edges.
      - The number of edges is 10x the number of persons
      - The direction of edges indicates the person IDs of who is following whom
        * `to` is whoever is being followed, `from` is whoever is doing the following
    """
    NUM_EDGES = len(persons_df) * 10
    # Obtain a random list of person IDs with repetition
    ids_1 = np.random.choice(persons_df["id"], size=NUM_EDGES, replace=True)
    ids_2 = np.random.choice(persons_df["id"], size=NUM_EDGES, replace=True)
    # Create edges dataframe
    edges_df = pl.DataFrame({"to": ids_1, "from": ids_2})
    # Prevent self-connecting edges
    edges_df = edges_df.filter(pl.col("to") != pl.col("from")).sort(["to", "from"])
    print(f"Generated {edges_df.shape[0]} edges in total without self-connections")
    return edges_df


def create_super_node_edges(persons_df: pl.DataFrame) -> pl.DataFrame:
    """
    Add some super nodes to the graph to make it more interesting.
    A "super node" is a person who has a large number of followers.
      - The aim is to have a select few persons act as as concentration points in the graph
      - The number of super nodes is set as a fraction of the total number of persons in the graph
    """
    NUM_SUPER_NODES = len(persons_df) * 5 // 1000
    super_node_ids = np.random.choice(persons_df["id"], size=NUM_SUPER_NODES, replace=False)
    # Convert to dataframe
    super_nodes_df = pl.DataFrame({"id": super_node_ids}).sort("id")
    print(f"Generated {len(super_nodes_df)} super nodes for {len(persons_df)} persons")
    # Let's assume super nodes are connected to anywhere between 0.5-5% of the graph
    lower_bound = len(persons_df) * 5 // 1000
    upper_bound = len(persons_df) * 5 // 100
    # Generate a random number between lower/upper bounds for each super node to connect to
    super_nodes_df = super_nodes_df.with_columns(
        pl.lit(
            np.random.randint(
                lower_bound,
                upper_bound,
                len(super_nodes_df),
            )
        ).alias("num_connections")
    )
    # Generate a list of edge connections for each super node, with length between lower/upper bounds
    super_nodes_df = (
        # Take in the column val of num_connections and return a list of IDs from persons_df
        super_nodes_df.with_columns(
            pl.col("num_connections")
            .apply(lambda x: select_random_ids(persons_df, x))
            .alias("connections")
        )
        # Explode the connections column to create a row for each connection
        .explode("connections")
        .filter(
            pl.col("id") != pl.col("connections")
        )
        .sort(["id", "connections"])
        .select(["id", "connections"])
    )
    # Ensure columns have the same name as edges_df for concatenation
    super_nodes_df = super_nodes_df.rename({"id": "to", "connections": "from"})
    return super_nodes_df


def main() -> None:
    persons_df = get_persons_df(NODES_PATH / "persons.csv")
    np.random.seed(SEED)
    edges_df = get_initial_person_edges(persons_df)
    # Generate edges from super nodes
    super_node_edges_df = create_super_node_edges(persons_df)
    # Concatenate edges from original edges_df and super_node_edges_df
    edges_df = (
        pl.concat([edges_df, super_node_edges_df])
        .unique()
        .sort(["to", "from"])
    )
    # Limit the number of edges
    if NUM < len(edges_df):
        edges_df = edges_df.head(NUM)
        print(f"Limiting edges to {NUM} per the `--num` argument")
    # Write nodes
    edges_df.write_csv(Path("output/edges") / "followers.csv", separator="|")
    print(f"Wrote {len(edges_df)} edges for {len(persons_df)} persons")


if __name__ == "__main__":
    # fmt: off
    parser = argparse.ArgumentParser()
    parser.add_argument("--num", "-n", type=int, default=int(1E9), help="Number of edges to limit the result to")
    parser.add_argument("--seed", "-s", type=int, default=0, help="Random seed")
    args = parser.parse_args()
    # fmt: on

    SEED = args.seed
    NUM = args.num
    NODES_PATH = Path("output/nodes")
    # Create output dir
    Path("output/edges").mkdir(parents=True, exist_ok=True)

    # Ensure that a global seed is set prior to running main
    np.random.seed(SEED)
    main()
