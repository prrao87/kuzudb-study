"""
Generate edges between persons and their interests
"""
import argparse
from pathlib import Path

import numpy as np
import polars as pl


def select_random_ids(df: pl.DataFrame, colname: str, num: int) -> list[int]:
    """Select random IDs from a column of a dataframe"""
    connections = list(np.random.choice(df[colname], size=num, replace=False))
    return connections


def main() -> None:
    interests_df = pl.read_parquet(Path(NODES_PATH) / "interests.parquet").rename(
        {"id": "interest_id"}
    )
    # Read in person IDs
    persons_df = pl.read_parquet(NODES_PATH / "persons.parquet").select("id")
    # Set a lower and upper bound on the number of interests per person
    lower_bound, upper_bound = 1, 5
    # Add a column with a random number of interests per person
    persons_df = persons_df.with_columns(
        pl.lit(
            np.random.randint(
                lower_bound,
                upper_bound,
                len(persons_df),
            )
        ).alias("num_interests")
    )
    # Add a column of random IDs from the interests_df, and explode it within the DataFrame
    edges_df = (
        # Take in the column val of num_connections and return a list of IDs from persons_df
        persons_df.with_columns(
            pl.col("num_interests")
            .apply(lambda x: select_random_ids(interests_df, "interest_id", x))
            .alias("interests")
        )
        # Explode the connections column to create a row for each connection
        .explode("interests")
        .sort(["id", "interests"])
        .select(["id", "interests"])
    )
    # Limit the number of edges
    if NUM < len(edges_df):
        edges_df = edges_df.head(NUM)
        print(f"Limiting edges to {NUM} per the `--num` argument")
    # Write nodes
    edges_df = edges_df.rename({"id": "from", "interests": "to"})
    edges_df.write_parquet(Path("output/edges") / "interests.parquet")
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
