"""
Run a series of queries on the Neo4j database
"""
import polars as pl
import kuzu
from kuzu import Connection
from typing import Any
from codetiming import Timer


def run_query1(conn: Connection) -> None:
    "Who are the top 3 most-followed persons in the network?"
    query = """
        MATCH (follower:Person)-[:Follows]->(person:Person)
        RETURN person.id AS personID, person.name AS name, count(follower.id) AS numFollowers
        ORDER BY numFollowers DESC LIMIT 3;
    """
    with Timer(name="query1", text="Query 1 completed in {:.6f}s"):
        response = conn.execute(query)
        result = pl.from_arrow(response.get_as_arrow(chunk_size=1000))
    print(f"\nQuery 1:\n {query}")
    print(f"Top 3 most-followed persons:\n{result}")


def run_query2(conn: Connection) -> None:
    "In which city does the most-followed person in the network live?"
    query = """
        MATCH (follower:Person)-[:Follows]->(person:Person)
        WITH person, count(follower.id) as numFollowers
        ORDER BY numFollowers DESC LIMIT 1
        MATCH (person) -[:LivesIn]-> (city:City)
        RETURN person.name AS name, numFollowers, city.city AS city, city.state AS state, city.country AS country;
    """
    with Timer(name="query2", text="Query 2 completed in {:.6f}s"):
        response = conn.execute(query)
        result = pl.from_arrow(response.get_as_arrow(chunk_size=1000))
    print(f"\nQuery 2:\n {query}")
    print(f"City in which most-followed person lives:\n{result}")


def run_query3(conn: Connection, params: list[tuple[str, Any]]) -> None:
    "Which are the top 5 cities in a particular region of the world with the lowest average age in the network?"
    query = """
        MATCH (p:Person) -[:LivesIn]-> (c:City)-[*1..2]-> (co:Country {country: $country})
        RETURN c.city AS city, avg(p.age) AS averageAge
        ORDER BY averageAge LIMIT 5;
    """
    with Timer(name="query3", text="Query 3 completed in {:.6f}s"):
        response = conn.execute(query, parameters=params)
        result = pl.from_arrow(response.get_as_arrow(chunk_size=1000))
    print(f"\nQuery 3:\n {query}")
    print(f"Cities with lowest average age in {params[0][1]}:\n{result}")


def run_query4(conn: Connection, params: list[tuple[str, Any]]) -> None:
    "How many persons between a certain age range are in each country?"
    query = """
        MATCH (p:Person)-[:LivesIn]->(ci:City)-[*1..2]->(country:Country)
        WHERE p.age > $age_lower AND p.age < $age_upper
        RETURN country.country AS countries, count(country) AS personCounts
        ORDER BY personCounts DESC LIMIT 3;
    """
    with Timer(name="query4", text="Query 4 completed in {:.6f}s"):
        response = conn.execute(query, parameters=params)
    print(f"\nQuery 4:\n {query}")
    result = pl.from_arrow(response.get_as_arrow(chunk_size=1000))
    print(f"Persons between ages {params[0][1]}-{params[1][1]} in each country:\n{result}")


def main(conn: Connection) -> None:
    with Timer(name="queries", text="Queries completed in {:.4f}s"):
        run_query1(conn)
        run_query2(conn)
        run_query3(conn, params=[("country", "Canada")])
        run_query4(conn, params=[("age_lower", 30), ("age_upper", 40)])


if __name__ == "__main__":
    DB_NAME = "social_network"
    db = kuzu.Database(f"./{DB_NAME}")
    CONNECTION = kuzu.Connection(db)

    main(CONNECTION)

