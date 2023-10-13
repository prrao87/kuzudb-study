"""
Generate edges between cities and the states to which they belong
"""
from pathlib import Path

import polars as pl


def main() -> None:
    # Read data from cities file
    cities_df = (
        pl.read_parquet(NODES_PATH / "cities.parquet")
        .rename({"id": "city_id"})
        .select(["city_id", "city", "state"])
    )
    # Read in states from file
    states_df = (
        pl.read_parquet(NODES_PATH / "states.parquet")
        .rename({"id": "state_id"})
        .select("state_id", "state")
    )
    # Join city and state dataframes on name
    edges_df = (
        states_df.join(cities_df, on="state", how="left")
        .select(["city_id", "state_id"])
        .rename({"city_id": "from", "state_id": "to"})
    )
    # Write nodes
    edges_df.write_parquet(Path("output/edges") / "city_in.parquet", compression="snappy")
    print(f"Wrote {len(edges_df)} edges for {len(cities_df)} cities")


if __name__ == "__main__":
    NODES_PATH = Path("output/nodes")
    # Create output dir
    Path("output/edges").mkdir(parents=True, exist_ok=True)

    main()
