"""
Generate nodes for a person's interests
These are activities or hobbies person in the real world might have
"""
from pathlib import Path
import polars as pl


def main(filename: str) -> pl.DataFrame:
    """
    For now we just use a static hand-coded list of interest categories
    """
    interests = pl.read_csv(filename)
    # Sort values, remove empties and de-duplicate
    interests_df = interests.filter(pl.col("interest") != "").unique().sort("interest")
    # Add ID column to function as a primary key
    ids = list(range(1, len(interests_df) + 1))
    interests_df = interests_df.with_columns(pl.lit(ids).alias("id"))
    # Write to csv
    interests_df.select(pl.col("id"), pl.all().exclude("id")).write_csv(
        Path("output/nodes") / "interests.csv", separator="|"
    )
    return interests


if __name__ == "__main__":
    main("raw/interests.csv")
