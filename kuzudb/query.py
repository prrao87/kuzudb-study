"""
Run a series of queries on the Neo4j database
"""
from typing import Any

import kuzu
import polars as pl
from codetiming import Timer
from kuzu import Connection


def run_query1(conn: Connection) -> None:
    "Who are the top 3 most-followed persons in the network?"
    query = """
        MATCH (follower:Person)-[:Follows]->(person:Person)
        RETURN person.id AS personID, person.name AS name, count(follower.id) AS numFollowers
        ORDER BY numFollowers DESC LIMIT 3;
    """
    print(f"\nQuery 1:\n {query}")
    with Timer(name="query1", text="Query 1 completed in {:.6f}s"):
        response = conn.execute(query)
        result = pl.from_arrow(response.get_as_arrow(chunk_size=1000))
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
    print(f"\nQuery 2:\n {query}")
    with Timer(name="query2", text="Query 2 completed in {:.6f}s"):
        response = conn.execute(query)
        result = pl.from_arrow(response.get_as_arrow(chunk_size=1000))
        print(f"City in which most-followed person lives:\n{result}")


def run_query3(conn: Connection, params: list[tuple[str, Any]]) -> None:
    "Which are the top 5 cities in a particular region of the world with the lowest average age in the network?"
    query = """
        MATCH (p:Person) -[:LivesIn]-> (c:City)-[*1..2]-> (co:Country {country: $country})
        RETURN c.city AS city, avg(p.age) AS averageAge
        ORDER BY averageAge LIMIT 5;
    """
    print(f"\nQuery 3:\n {query}")
    with Timer(name="query3", text="Query 3 completed in {:.6f}s"):
        response = conn.execute(query, parameters=params)
        result = pl.from_arrow(response.get_as_arrow(chunk_size=1000))
        print(f"Cities with lowest average age in {params[0][1]}:\n{result}")


def run_query4(conn: Connection, params: list[tuple[str, Any]]) -> None:
    "How many persons between a certain age range are in each country?"
    query = """
        MATCH (p:Person)-[:LivesIn]->(ci:City)-[*1..2]->(country:Country)
        WHERE p.age >= $age_lower AND p.age <= $age_upper
        RETURN country.country AS countries, count(country) AS personCounts
        ORDER BY personCounts DESC LIMIT 3;
    """
    print(f"\nQuery 4:\n {query}")
    with Timer(name="query4", text="Query 4 completed in {:.6f}s"):
        response = conn.execute(query, parameters=params)
        result = pl.from_arrow(response.get_as_arrow(chunk_size=1000))
        print(f"Persons between ages {params[0][1]}-{params[1][1]} in each country:\n{result}")


def run_query5(conn: Connection, params: list[tuple[str, Any]]) -> None:
    "How many persons between a certain age range are in each country?"
    query = """
        MATCH (p:Person)-[:HasInterest]->(i:Interest)
        WHERE lower(i.interest) = lower($interest)
        AND lower(p.gender) = lower($gender)
        WITH p, i
        MATCH (p)-[:LivesIn]->(c:City)
        WHERE c.city = $city AND c.country = $country
        RETURN count(p) AS numPersons
    """
    print(f"\nQuery 5:\n {query}")
    with Timer(name="query5", text="Query 5 completed in {:.6f}s"):
        response = conn.execute(query, parameters=params)
        result = pl.from_arrow(response.get_as_arrow(chunk_size=1000))
        print(
            f"Number of {params[0][1]} users in {params[1][1]}, {params[2][1]} who have an interest in {params[3][1]}:\n{result}"
        )


def run_query6(conn: Connection, params: list[tuple[str, Any]]) -> None:
    "How many persons between a certain age range are in each country?"
    query = """
        MATCH (p:Person)-[:HasInterest]->(i:Interest)
        WHERE lower(i.interest) = lower($interest)
        AND lower(p.gender) = lower($gender)
        WITH p, i
        MATCH (p)-[:LivesIn]->(c:City)
        RETURN count(p.id) AS numPersons, c.city, c.country
        ORDER BY numPersons DESC LIMIT 5
    """
    print(f"\nQuery 6:\n {query}")
    with Timer(name="query6", text="Query 6 completed in {:.6f}s"):
        response = conn.execute(query, parameters=params)
        result = pl.from_arrow(response.get_as_arrow(chunk_size=1000))
        print(
            f"City with the most {params[0][1]} users who have an interest in {params[1][1]}:\n{result}"
        )


def run_query7(conn: Connection, params: list[tuple[str, Any]]) -> None:
    "How many persons between a certain age range are in each country?"
    query = """
        MATCH (p:Person)-[:LivesIn]->(:City)-[:CityIn]->(s:State)
        WHERE p.age >= $age_lower AND p.age <= $age_upper AND s.country = $country
        WITH p, s
        MATCH (p)-[:HasInterest]->(i:Interest)
        WHERE lower(i.interest) = lower($interest)
        RETURN count(p.id) AS numPersons, s.state AS state, s.country AS country
        ORDER BY numPersons DESC LIMIT 1
    """
    print(f"\nQuery 7:\n {query}")
    with Timer(name="query7", text="Query 7 completed in {:.6f}s"):
        response = conn.execute(query, parameters=params)
        result = pl.from_arrow(response.get_as_arrow(chunk_size=1000))
        print(
            f"""
            State in {params[0][1]} with the most users between ages {params[1][1]}-{params[2][1]} who have an interest in {params[3][1]}:\n{result}
            """
        )


def run_query8(conn: Connection) -> None:
    query = """
        MATCH (p1:Person)-[f:Follows]->(p2:Person)
        WHERE p1.id > p2.id
        RETURN count(f) as numFollowers
    """
    print(f"\nQuery 8:\n {query}")
    with Timer(name="query8", text="Query 8 completed in {:.6f}s"):
        response = conn.execute(query)
        result = pl.from_arrow(response.get_as_arrow(chunk_size=1000))
        print(f"Number of second degree connections reachable in the graph:\n{result}")


def main(conn: Connection) -> None:
    with Timer(name="queries", text="Queries completed in {:.4f}s"):
        run_query1(conn)
        run_query2(conn)
        run_query3(conn, params=[("country", "Canada")])
        run_query4(conn, params=[("age_lower", 30), ("age_upper", 40)])
        run_query5(
            conn,
            params=[
                ("gender", "male"),
                ("city", "London"),
                ("country", "United Kingdom"),
                ("interest", "fine dining"),
            ],
        )
        run_query6(conn, params=[("gender", "female"), ("interest", "tennis")])
        run_query7(
            conn,
            params=[
                ("country", "United States"),
                ("age_lower", 23),
                ("age_upper", 30),
                ("interest", "photography"),
            ],
        )
        run_query8(conn)


if __name__ == "__main__":
    DB_NAME = "social_network"
    db = kuzu.Database(f"./{DB_NAME}")
    CONNECTION = kuzu.Connection(db)
    # For a fairer comparison with Neo4j, where “Transactions are single-threaded, confined, and independent.”
    CONNECTION.set_max_threads_for_exec(1)

    main(CONNECTION)
