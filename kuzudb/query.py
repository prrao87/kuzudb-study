"""
Run a series of queries on an existing Kùzu database
"""
from typing import Any

import kuzu
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
    response = conn.execute(query)
    result = response.get_as_pl()
    print(f"Top 3 most-followed persons:\n{result}")
    return result


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
    response = conn.execute(query)
    result = response.get_as_pl()
    print(f"City in which most-followed person lives:\n{result}")
    return result


def run_query3(conn: Connection, params: list[tuple[str, Any]]) -> None:
    "Which 5 cities in a particular country have the lowest average age in the network?"
    query = """
        MATCH (p:Person) -[:LivesIn]-> (c:City) -[*1..2]-> (co:Country)
        WHERE co.country = $country
        RETURN c.city AS city, avg(p.age) AS averageAge
        ORDER BY averageAge LIMIT 5;
    """
    print(f"\nQuery 3:\n {query}")
    response = conn.execute(query, parameters=params)
    result = response.get_as_pl()
    print(f"Cities with lowest average age in {params['country']}:\n{result}")
    return result


def run_query4(conn: Connection, params: list[tuple[str, Any]]) -> None:
    "How many persons between a certain age range are in each country?"
    query = """
        MATCH (p:Person)-[:LivesIn]->(ci:City)-[*1..2]->(country:Country)
        WHERE p.age >= $age_lower AND p.age <= $age_upper
        RETURN country.country AS countries, count(country) AS personCounts
        ORDER BY personCounts DESC LIMIT 3;
    """
    print(f"\nQuery 4:\n {query}")
    response = conn.execute(query, parameters=params)
    result = response.get_as_pl()
    print(f"Persons between ages {params['age_lower']}-{params['age_upper']} in each country:\n{result}")
    return result


def run_query5(conn: Connection, params: list[tuple[str, Any]]) -> None:
    "How many men in a particular city have an interest in the same thing?"
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
    response = conn.execute(query, parameters=params)
    result = response.get_as_pl()
    print(
        f"Number of {params['gender']} users in {params['city']}, {params['country']} who have an interest in {params['interest']}:\n{result}"
    )
    return result


def run_query6(conn: Connection, params: list[tuple[str, Any]]) -> None:
    "Which city has the maximum number of people of a particular gender that share a particular interest"
    query = """
        MATCH (p:Person)-[:HasInterest]->(i:Interest)
        WHERE lower(i.interest) = lower($interest)
        AND lower(p.gender) = lower($gender)
        WITH p, i
        MATCH (p)-[:LivesIn]->(c:City)
        RETURN count(p.id) AS numPersons, c.city AS city, c.country AS country
        ORDER BY numPersons DESC LIMIT 5
    """
    print(f"\nQuery 6:\n {query}")
    response = conn.execute(query, parameters=params)
    result = response.get_as_pl()
    print(
        f"City with the most {params['gender']} users who have an interest in {params['interest']}:\n{result}"
    )
    return result


def run_query7(conn: Connection, params: list[tuple[str, Any]]) -> None:
    "Which U.S. state has the maximum number of persons between a specified age who enjoy a particular interest?"
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
    response = conn.execute(query, parameters=params)
    result = response.get_as_pl()
    print(
        f"""
        State in {params['country']} with the most users between ages {params['age_lower']}-{params['age_upper']} who have an interest in {params['interest']}:\n{result}
        """
    )
    return result


def run_query8(conn: Connection) -> None:
    "How many second-degree paths exist in the graph?"
    query = """
        MATCH (a:Person)-[r1:Follows]->(b:Person)-[r2:Follows]->(c:Person)
        RETURN count(*) AS numPaths
    """
    print(f"\nQuery 8:\n {query}")
    response = conn.execute(query)
    result = response.get_as_pl()
    print(
        f"""
        Number of second-degree paths:\n{result}
        """
    )
    return result


def run_query9(conn: Connection, params: list[tuple[str, Any]]) -> None:
    "How many paths exist in the graph through persons below a certain age to persons above a certain age?"
    query = """
        MATCH (a:Person)-[r1:Follows]->(b:Person)-[r2:Follows]->(c:Person)
        WHERE b.age < $age_1 AND c.age > $age_2
        RETURN count(*) as numPaths
    """

    print(f"\nQuery 9:\n {query}")
    response = conn.execute(query, parameters=params)
    result = response.get_as_pl()
    print(
        f"""
        Number of paths through persons below {params['age_1']} to persons above {params['age_2']}:\n{result}
        """
    )
    return result


def main(conn: Connection) -> None:
    with Timer(name="queries", text="Queries completed in {:.4f}s"):
        _ = run_query1(conn)
        _ = run_query2(conn)
        _ = run_query3(conn, params={"country": "United States"})
        _ = run_query4(conn, params={"age_lower": 30, "age_upper": 40})
        _ = run_query5(
            conn,
            params={
                "gender": "male",
                "city": "London",
                "country": "United Kingdom",
                "interest": "fine dining",
            },
        )
        _ = run_query6(conn, params={"gender": "female", "interest": "tennis"})
        _ = run_query7(
            conn,
            params={
                "country": "United States",
                "age_lower": 23,
                "age_upper": 30,
                "interest": "photography",
            },
        )
        _ = run_query8(conn)
        _ = run_query9(conn, params={"age_1": 50, "age_2": 25})


if __name__ == "__main__":
    DB_NAME = "social_network"
    db = kuzu.Database(f"./{DB_NAME}")
    # Default num_threads=0 uses as many threads as hardware and utilization allows
    CONNECTION = kuzu.Connection(db, num_threads=0)

    main(CONNECTION)
