"""
Generate edges between persons and their residence locations
"""

import argparse
from pathlib import Path

import numpy as np
import polars as pl


def get_persons_df(filepath: Path) -> pl.DataFrame:
    # Read in persons data
    persons_df = pl.read_parquet(filepath).select("id")
    return persons_df


def get_cities_df(filepath: Path) -> pl.DataFrame:
    """
    Get only cities with a population of > 1M
    """
    # Read in cities data and rename the ID column to avoid conflicts
    residence_loc_df = (
        pl.read_parquet(filepath)
        .filter(pl.col("population") >= 1_000_000)
        .rename({"id": "city_id"})
    )
    return residence_loc_df


def main() -> None:
    np.random.seed(SEED)
    persons_df = get_persons_df(NODES_PATH / "persons.parquet")
    residence_loc_df = get_cities_df(NODES_PATH / "cities.parquet")
    # Randomly pick a city ID from the list of all cities with population > 1M
    city_ids = np.random.choice(residence_loc_df["city_id"], size=len(persons_df), replace=True)
    # Obtain top 5 most common cities name via a join
    city_ids_df = pl.DataFrame(city_ids).rename({"column_0": "city_id"})
    # Horizontally stack the person IDs and the residence city IDs to create a list of edges
    edges_df = pl.concat([persons_df, city_ids_df], how="horizontal")
    city_counts_df = edges_df.group_by("city_id").len().sort("len", descending=True)
    top_cities_df = (
        city_counts_df.join(residence_loc_df, on="city_id", how="left")
        # List top 5 cities
        .sort("len", descending=True)
        .head(5)
    )
    top_5 = top_cities_df["city"].to_list()
    # Limit the number of edges
    if NUM < len(edges_df):
        edges_df = edges_df.head(NUM)
        print(f"Limiting edges to {NUM} per the `--num` argument")
    # Write nodes
    edges_df = edges_df.rename({"city_id": "to", "id": "from"}).write_parquet(
        Path("output/edges") / "lives_in.parquet",
    )
    print(f"Generated residence cities for persons. Top 5 common cities are: {', '.join(top_5)}")


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
