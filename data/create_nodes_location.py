"""
Generate nodes for cities, states and countries
"""
import argparse
import unicodedata
from pathlib import Path
from typing import Any

import polars as pl

City = dict[str, Any]


def remove_accents(input_str: str) -> str:
    """
    Normalize unicode data, remove diacritical marks and convert to ASCII
    https://docs.python.org/3/library/unicodedata.html#unicodedata.normalize
    """
    nfkd_form = unicodedata.normalize("NFKD", input_str)
    only_ascii = nfkd_form.encode("ASCII", "ignore").decode("utf-8")
    return only_ascii


def get_cities_df(world_cities: pl.DataFrame) -> pl.DataFrame:
    # For simplicity we only extract cities from the following countries
    country_codes = ["US", "GB", "CA"]
    cities_of_interest = world_cities.filter(pl.col("iso2").is_in(country_codes))
    print(f"Obtained {cities_of_interest.shape[0]} cities from countries: {country_codes}")
    # Ensure polulation column is cast to type integer
    cities_of_interest = cities_of_interest.with_columns(
        pl.col("population").cast(pl.Float32).cast(pl.Int32)
    )
    return cities_of_interest


def write_city_nodes(cities_of_interest: pl.DataFrame) -> pl.DataFrame:
    # Convert states column to ascii as it has problematic characters
    cities_of_interest = cities_of_interest.with_columns(
        pl.col("admin_name").map_elements(remove_accents)
    ).drop("city")
    # Rename columns
    cities_of_interest = cities_of_interest.rename({"city_ascii": "city", "admin_name": "state"})
    # Isolate just city metadata for city nodes, and remove those with empty state values
    city_nodes = (
        cities_of_interest.select(
            "city",
            "state",
            "country",
            "lat",
            "lng",
            "population",
        )
        .filter(pl.col("state") != "")
        .sort(["country", "state", "city"])
    )
    # Add ID column to function as a primary key
    ids = list(range(1, len(city_nodes) + 1))
    city_nodes = city_nodes.with_columns(pl.Series(ids).alias("id"))
    # Write to csv
    city_nodes.select(pl.col("id"), pl.all().exclude("id")).write_parquet(
        Path("output/nodes") / "cities.parquet"
    )
    print(f"Wrote {city_nodes.shape[0]} cities to parquet")
    return city_nodes


def write_state_nodes(city_nodes: pl.DataFrame) -> None:
    # Obtain unique list of states and countries
    state_nodes = city_nodes.select("state", "country").unique().sort(["country", "state"])
    # Add ID column to function as a primary key
    ids = list(range(1, len(state_nodes) + 1))
    state_nodes = state_nodes.with_columns(pl.Series(ids).alias("id"))
    # Write to csv
    state_nodes.select(pl.col("id"), pl.all().exclude("id")).write_parquet(
        Path("output/nodes") / "states.parquet"
    )
    print(f"Wrote {state_nodes.shape[0]} states to parquet")


def write_country_nodes(city_nodes: pl.DataFrame) -> None:
    # Obtain unique list of countries
    country_nodes = city_nodes.select("country").unique().sort("country", descending=False)
    # Add ID column to function as a primary key
    ids = list(range(1, len(country_nodes) + 1))
    country_nodes = country_nodes.with_columns(pl.Series(ids).alias("id"))
    # Write to csv
    country_nodes.select(pl.col("id"), pl.all().exclude("id")).write_parquet(
        Path("output/nodes") / "countries.parquet"
    )
    print(f"Wrote {country_nodes.shape[0]} countries to parquet")


def main(input_file: str) -> None:
    world_cities = pl.read_csv(input_file, infer_schema_length=10_000)
    cities_of_interest = get_cities_df(world_cities)
    if NUM > 0:
        cities_of_interest = cities_of_interest.head(NUM)
    # Cities
    city_nodes = write_city_nodes(cities_of_interest)
    # States
    write_state_nodes(city_nodes)
    # Countries
    write_country_nodes(city_nodes)


if __name__ == "__main__":
    # fmt: off
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", type=str, default="raw/worldcities.csv", help="Input file for raw location info")
    parser.add_argument("--num", "-n", type=int, default=10_000, help="Limit the number of locations to generate")
    parser.add_argument("--seed", "-s", type=int, default=0, help="Random seed")
    args = parser.parse_args()
    # fmt: on

    SEED = args.seed
    NUM = args.num
    INPUT_FILE = args.input_file
    # Create output dirs
    Path("output/nodes").mkdir(parents=True, exist_ok=True)
    Path("output/edges").mkdir(parents=True, exist_ok=True)

    main(INPUT_FILE)
