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
    query = """
        MATCH (follower:Person)-[:FOLLOWS]->(person:Person)
        RETURN person.personID AS personID, person.name AS name, count(follower) AS numFollowers
        ORDER BY numFollowers DESC LIMIT 3
    """
    print(f"\nQuery 1:\n {query}")
    with Timer(name="query1", text="Query 1 completed in {:.6f}s"):
        response = session.run(query)
        result = pl.from_dicts(response.data())
        print(f"Top 3 most-followed persons:\n{result}")


def run_query2(session: Session) -> None:
    query = """
        MATCH (follower:Person) -[:FOLLOWS]-> (person:Person)
        WITH person, count(follower) as followers
        ORDER BY followers DESC LIMIT 1
        MATCH (person) -[:LIVES_IN]-> (city:City)
        RETURN person.name AS name, followers AS numFollowers, city.city AS city, city.state AS state, city.country AS country
    """
    print(f"\nQuery 2:\n {query}")
    with Timer(name="query2", text="Query 2 completed in {:.6f}s"):
        response = session.run(query)
        result = pl.from_dicts(response.data())
        print(f"City in which most-followed person lives:\n{result}")


def run_query3(session: Session, country: str) -> None:
    query = """
        MATCH (p:Person) -[:LIVES_IN]-> (c:City) -[*1..2]-> (co:Country {country: $country})
        RETURN c.city AS city, avg(p.age) AS averageAge
        ORDER BY averageAge LIMIT 5
    """
    print(f"\nQuery 3:\n {query}")
    with Timer(name="query3", text="Query 3 completed in {:.6f}s"):
        response = session.run(query, country=country)
        result = pl.from_dicts(response.data())
        print(f"Cities with lowest average age in {country}:\n{result}")


def run_query4(session: Session, age_lower: int, age_upper: int) -> None:
    query = """
        MATCH (p:Person)-[:LIVES_IN]->(ci:City)-[*1..2]->(country:Country)
        WHERE p.age >= $age_lower AND p.age <= $age_upper
        RETURN country.country AS countries, count(country) AS personCounts
        ORDER BY personCounts DESC LIMIT 3
    """
    print(f"\nQuery 4:\n {query}")
    with Timer(name="query4", text="Query 4 completed in {:.6f}s"):
        response = session.run(query, age_lower=age_lower, age_upper=age_upper)
        result = pl.from_dicts(response.data())
        print(f"Persons between ages {age_lower}-{age_upper} in each country:\n{result}")


def run_query5(session: Session, gender: str, city: str, country: str, interest: str) -> None:
    query = """
        MATCH (p:Person)-[:HAS_INTEREST]->(i:Interest)
        WHERE tolower(i.interest) = tolower($interest)
        AND tolower(p.gender) = tolower($gender)
        WITH p, i
        MATCH (p)-[:LIVES_IN]->(c:City)
        WHERE c.city = $city AND c.country = $country
        RETURN count(p) AS numPersons
    """
    print(f"\nQuery 5:\n {query}")
    with Timer(name="query5", text="Query 5 completed in {:.6f}s"):
        response = session.run(query, gender=gender, city=city, country=country, interest=interest)
        result = pl.from_dicts(response.data())
        print(f"Number of {gender} users in {city}, {country} who have an interest in {interest}:\n{result}")


def run_query6(session: Session, gender: str, interest: str) -> None:
    query = """
        MATCH (p:Person)-[:HAS_INTEREST]->(i:Interest)
        WHERE tolower(i.interest) = tolower($interest)
        AND tolower(p.gender) = tolower($gender)
        WITH p, i
        MATCH (p)-[:LIVES_IN]->(c:City)
        RETURN count(p) AS numPersons, c.city, c.country
        ORDER BY numPersons DESC LIMIT 5
    """
    print(f"\nQuery 6:\n {query}")
    with Timer(name="query6", text="Query 6 completed in {:.6f}s"):
        response = session.run(query, gender=gender, interest=interest)
        result = pl.from_dicts(response.data())
        print(f"City with the most {gender} users who have an interest in {interest}:\n{result}")


def run_query7(session: Session, country: str, age_lower: int, age_upper: int, interest: str) -> None:
    query = """
        MATCH (p:Person)-[:LIVES_IN]->(:City)-[:CITY_IN]->(s:State)
        WHERE p.age >= $age_lower AND p.age <= $age_upper AND s.country = $country
        WITH p, s
        MATCH (p)-[:HAS_INTEREST]->(i:Interest)
        WHERE tolower(i.interest) = tolower($interest)
        RETURN count(p) AS numPersons, s.state AS state, s.country AS country
        ORDER BY numPersons DESC LIMIT 1
    """
    print(f"\nQuery 7:\n {query}")
    with Timer(name="query7", text="Query 7 completed in {:.6f}s"):
        response = session.run(query, country=country, age_lower=age_lower, age_upper=age_upper, interest=interest)
        result = pl.from_dicts(response.data())
        print(
            f"""
            State in {country} with the most users between ages {age_lower}-{age_upper} who have an interest in {interest}:\n{result}
            """
        )


def run_query8(session: Session) -> None:
    query = """
        MATCH (p1:Person)-[f:FOLLOWS]->(p2:Person)
        WHERE p1.personID > p2.personID
        RETURN count(f) as numFollowers
    """
    print(f"\nQuery 8:\n {query}")
    with Timer(name="query8", text="Query 8 completed in {:.6f}s"):
        response = session.run(query)
        result = pl.from_dicts(response.data())
        print(f"Number of second degree connections reachable in the graph:\n{result}")


def main() -> None:
    with GraphDatabase.driver(URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
        with driver.session(database="neo4j") as session:
            with Timer(name="queries", text="Query script completed in {:.6f}s"):
                run_query1(session)
                run_query2(session)
                run_query3(session, country="Canada")
                run_query4(session, age_lower=30, age_upper=40)
                run_query5(session, gender="male", city="London", country="United Kingdom", interest="fine dining")
                run_query6(session, gender="female", interest="tennis")
                run_query7(session, country="United States", age_lower=23, age_upper=30, interest="photography")
                run_query8(session)


if __name__ == "__main__":
    main()
