import argparse
from datetime import date
from pathlib import Path
from typing import Any


import polars as pl
from faker import Faker

Profile = dict[str, Any]


def generate_fake_profiles(num: int, gender: str = "female") -> list[Profile]:
    """Generate fake profile for either a man or woman"""
    print(f"""Generate {num} fake {gender} profiles.""")
    profiles = []
    for _ in range(num):
        profile = dict()
        if gender == "female":
            profile["name"] = f"{fake.first_name_female()} {fake.last_name_female()}"
        else:
            assert gender == "male", "Please specify a gender of either male or female"
            profile["name"] = f"{fake.first_name_male()} {fake.last_name_male()}"
        profile["gender"] = gender
        profile["birthday"] = fake.date_between(start_date=date(1970, 1, 1), end_date=date(2000, 12, 31))
        profile["age"] = (date.today() - profile["birthday"]).days // 365
        profile["isMarried"] = fake.random_element(elements=(True, False))
        profiles.append(profile)
    return profiles


def create_person_df(male_profiles: list[Profile], female_profiles: list[Profile]) -> pl.DataFrame:
    # Combine profiles
    male_profiles_df = pl.from_dicts(male_profiles)
    female_profiles_df = pl.from_dicts(female_profiles)
    # Vertically stack male and female profiles and shuffle the rows
    persons_df = (
        male_profiles_df.vstack(female_profiles_df)
        .sample(fraction=1, shuffle=True, seed=SEED)
    )
    # Add ID column
    ids = list(range(1, len(persons_df) + 1))
    persons_df = persons_df.with_columns(pl.lit(ids).alias("id"))
    return persons_df


def main() -> None:
    num_male = NUM // 2
    num_female = NUM - num_male

    # Generate male profile
    female_profiles = generate_fake_profiles(num_female, gender="female")
    male_profiles = generate_fake_profiles(num_male, gender="male")
    
    # Create person dataframe
    persons_df = create_person_df(female_profiles, male_profiles)
    # Write nodes
    persons_df.select(
        pl.col("id"),
        pl.all().exclude("id")
    ).write_csv(Path("output/nodes") / "persons.csv", separator="|")
    print(f"Wrote {persons_df.shape[0]} person nodes to CSV")


if __name__ == "__main__":
    # fmt: off
    parser = argparse.ArgumentParser()
    parser.add_argument("--num", "-n", type=int, default=10_000, help="Number of fake profiles to generate")
    parser.add_argument("--seed", "-s", type=int, default=0, help="Random seed")
    args = parser.parse_args()
    # fmt: on

    SEED = args.seed
    NUM = args.num
    # Create faker object
    Faker.seed(SEED)
    fake = Faker()
    # Create output dirs
    Path("output/nodes").mkdir(parents=True, exist_ok=True)
    Path("output/edges").mkdir(parents=True, exist_ok=True)

    main()