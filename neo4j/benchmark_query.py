"""
Use the `pytest-benchmark` library to more formally benchmark the Neo4j queries wiht warmup and iterations.
`pip install pytest-benchmark`
"""
import os

import pytest
from dotenv import load_dotenv
from neo4j import GraphDatabase

import query

load_dotenv()


@pytest.fixture(scope="session")
def session():
    URI = "bolt://localhost:7687"
    NEO4J_USER = os.environ.get("NEO4J_USER")
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
    with GraphDatabase.driver(URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
        with driver.session(database="neo4j") as session:
            yield session


def test_benchmark_query1(benchmark, session):
    result = benchmark(query.run_query1, session)
    result = result.to_dicts()

    assert len(result) == 3
    assert result[0]["personID"] == 85723
    assert result[1]["personID"] == 68753
    assert result[2]["personID"] == 54696
    assert result[0]["numFollowers"] == 4998
    assert result[1]["numFollowers"] == 4985
    assert result[2]["numFollowers"] == 4976


def test_benchmark_query2(benchmark, session):
    result = benchmark(query.run_query2, session)
    result = result.to_dicts()

    assert len(result) == 1
    assert result[0]["name"] == "Melissa Murphy"
    assert result[0]["numFollowers"] == 4998
    assert result[0]["city"] == "Austin"
    assert result[0]["state"] == "Texas"
    assert result[0]["country"] == "United States"


def test_benchmark_query3(benchmark, session):
    result = benchmark(query.run_query3, session, "United States")
    result = result.to_dicts()

    assert len(result) == 5
    assert result[0]["city"] == "Austin"
    assert result[1]["city"] == "Kansas City"
    assert result[2]["city"] == "Miami"
    assert result[3]["city"] == "San Antonio"
    assert result[4]["city"] == "Houston"


def test_benchmark_query4(benchmark, session):
    result = benchmark(query.run_query4, session, 30, 40)
    result = result.to_dicts()

    assert len(result) == 3
    assert result[0]["countries"] == "United States"
    assert result[1]["countries"] == "Canada"
    assert result[2]["countries"] == "United Kingdom"
    assert result[0]["personCounts"] == 30680
    assert result[1]["personCounts"] == 3045
    assert result[2]["personCounts"] == 1801


def test_benchmark_query5(benchmark, session):
    result = benchmark(query.run_query5, session, "male", "London", "United Kingdom", "fine dining")
    result = result.to_dicts()

    assert len(result) == 1
    assert result[0]["numPersons"] == 52


def test_benchmark_query6(benchmark, session):
    result = benchmark(query.run_query6, session, "female", "tennis")
    result = result.to_dicts()

    assert len(result) == 5
    assert result[0]["numPersons"] == 66
    assert result[0]["city"] in ("Houston", "Birmingham")
    assert result[0]["country"] in ("United States", "United Kingdom")


def test_benchmark_query7(benchmark, session):
    result = benchmark(query.run_query7, session, "United States", 23, 30, "photography")
    result = result.to_dicts()

    assert len(result) == 1
    assert result[0]["numPersons"] == 141
    assert result[0]["state"] == "California"
    assert result[0]["country"] == "United States"


def test_benchmark_query8(benchmark, session):
    result = benchmark(query.run_query8, session)
    result = result.to_dicts()

    assert len(result) == 1
    assert result[0]["numPaths"] == 58431994


def test_benchmark_query9(benchmark, session):
    result = benchmark(query.run_query9, session, 50, 25)
    result = result.to_dicts()

    assert len(result) == 1
    assert result[0]["numPaths"] == 45578816
