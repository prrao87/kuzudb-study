"""
Run a series of queries on the Neo4j database
"""
import os

import polars as pl
from codetiming import Timer
from dotenv import load_dotenv
from neo4j import GraphDatabase, Session

load_dotenv()
# Config
URI = "bolt://localhost:7687"
NEO4J_USER = os.environ.get("NEO4J_USER")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")


def run_query1(session: Session) -> None:
    "Who are the top 3 most-followed persons in the network?"
    query = """
        MATCH (follower:Person)-[:FOLLOWS]->(person:Person)
        RETURN person.personID AS personID, person.name AS name, count(follower) AS numFollowers
        ORDER BY numFollowers DESC LIMIT 3
    """
    with Timer(name="query1", text="Query 1 completed in {:.6f}s"):
        response = session.run(query)
        result = pl.from_dicts(response.data())
    print(f"\nQuery 1:\n {query}")
    print(f"Top 3 most-followed persons:\n{result}")


def run_query2(session: Session) -> None:
    "In which city does the most-followed person in the network live?"
    query = """
        MATCH (follower:Person) -[:FOLLOWS]-> (person:Person)
        WITH person, count(follower) as followers
        ORDER BY followers DESC LIMIT 1
        MATCH (person) -[:LIVES_IN]-> (city:City)
        RETURN person.name AS name, followers AS numFollowers, city.city AS city, city.state AS state, city.country AS country
    """
    with Timer(name="query2", text="Query 2 completed in {:.6f}s"):
        response = session.run(query)
        result = pl.from_dicts(response.data())
    print(f"\nQuery 2:\n {query}")
    print(f"City in which most-followed person lives:\n{result}")


def run_query3(session: Session, country: str) -> None:
    "Which are the top 5 cities in a particular region of the world with the lowest average age in the network?"
    query = """
        MATCH (p:Person) -[:LIVES_IN]-> (c:City) -[*1..2]-> (co:Country {country: $country})
        RETURN c.city AS city, avg(p.age) AS averageAge
        ORDER BY averageAge LIMIT 5
    """
    with Timer(name="query3", text="Query 3 completed in {:.6f}s"):
        response = session.run(query, country=country)
        result = pl.from_dicts(response.data())
    print(f"\nQuery 3:\n {query}")
    print(f"Cities with lowest average age in {country}:\n{result}")


def run_query4(session: Session, age_lower: int, age_upper: int) -> None:
    "How many persons between a certain age range are in each country?"
    query = """
        MATCH (p:Person)-[:LIVES_IN]->(ci:City)-[*1..2]->(country:Country)
        WHERE p.age > $age_lower AND p.age < $age_upper
        RETURN country.country AS countries, count(country) AS personCounts
        ORDER BY personCounts DESC LIMIT 3
    """
    with Timer(name="query4", text="Query 4 completed in {:.6f}s"):
        response = session.run(query, age_lower=age_lower, age_upper=age_upper)
        result = pl.from_dicts(response.data())
    print(f"\nQuery 4:\n {query}")
    print(f"Persons between ages {age_lower}-{age_upper} in each country:\n{result}")


def main() -> None:
    with GraphDatabase.driver(URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
        with driver.session(database="neo4j") as session:
            with Timer(name="queries", text="Query script completed in {:.6f}s"):
                run_query1(session)
                run_query2(session)
                run_query3(session, country="Canada")
                run_query4(session, age_lower=30, age_upper=40)


if __name__ == "__main__":
    main()
