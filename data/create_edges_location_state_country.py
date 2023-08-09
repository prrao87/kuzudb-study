"""
Generate edges between states and the countries to which they belong
"""
from pathlib import Path

import polars as pl


def main() -> None:
    # Read in states from file
    states_df = (
        pl.read_csv(NODES_PATH / "states.csv", separator="|")
        .rename({"id": "state_id"})
        .select("state_id", "state", "country")
    )
    # Read data from countries file
    countries_df = (
        pl.read_csv(NODES_PATH / "countries.csv", separator="|")
        .rename({"id": "country_id"})
    )
    # Join city and state dataframes on name
    edges_df = (
        countries_df.join(states_df, on="country", how="left")
        .select(["state_id", "country_id"])
        .rename({"state_id": "from", "country_id": "to"})
    )
    # Write nodes
    edges_df.write_csv(Path("output/edges") / "state_in.csv", separator="|")
    print(f"Wrote {len(edges_df)} edges for {len(states_df)} states")


if __name__ == "__main__":
    NODES_PATH = Path("output/nodes")
    # Create output dir
    Path("output/edges").mkdir(parents=True, exist_ok=True)

    main()
