"""
Use the `pytest-benchmark` library to more formally benchmark the Kùzu queries with warmup and iterations.
`pip install pytest-benchmark`
"""
import pytest
import kuzu

import query


@pytest.fixture
def connection():
    db = kuzu.Database("./social_network")
    # Default num_threads=0 uses as many threads as hardware and utilization allows
    conn = kuzu.Connection(db, num_threads=0)
    yield conn


def test_benchmark_query1(benchmark, connection):
    result = benchmark(query.run_query1, connection)
    result = result.to_dicts()

    assert len(result) == 3
    assert result[0]["personID"] == 85723
    assert result[1]["personID"] == 68753
    assert result[2]["personID"] == 54696
    assert result[0]["numFollowers"] == 4998
    assert result[1]["numFollowers"] == 4985
    assert result[2]["numFollowers"] == 4976


def test_benchmark_query2(benchmark, connection):
    result = benchmark(query.run_query2, connection)
    result = result.to_dicts()

    assert len(result) == 1
    assert result[0]["name"] == "Melissa Murphy"
    assert result[0]["numFollowers"] == 4998
    assert result[0]["city"] == "Austin"
    assert result[0]["state"] == "Texas"
    assert result[0]["country"] == "United States"


def test_benchmark_query3(benchmark, connection):
    result = benchmark(query.run_query3, connection, {"country": "United States"})
    result = result.to_dicts()

    assert len(result) == 5
    assert result[0]["city"] == "Austin"
    assert result[1]["city"] == "Kansas City"
    assert result[2]["city"] == "Miami"
    assert result[3]["city"] == "San Antonio"
    assert result[4]["city"] == "Portland"


def test_benchmark_query4(benchmark, connection):
    result = benchmark(query.run_query4, connection, {"age_lower": 30, "age_upper": 40})
    result = result.to_dicts()

    assert len(result) == 3
    assert result[0]["countries"] == "United States"
    assert result[1]["countries"] == "Canada"
    assert result[2]["countries"] == "United Kingdom"
    assert result[0]["personCounts"] == 30712
    assert result[1]["personCounts"] == 3043
    assert result[2]["personCounts"] == 1809


def test_benchmark_query5(benchmark, connection):
    result = benchmark(
        query.run_query5,
        connection,
        {
            "gender": "male",
            "city": "London",
            "country": "United Kingdom",
            "interest": "fine dining",
        },
    )
    result = result.to_dicts()

    assert len(result) == 1
    assert result[0]["numPersons"] == 52


def test_benchmark_query6(benchmark, connection):
    result = benchmark(
        query.run_query6,
        connection,
        {
            "gender": "female",
            "interest": "tennis"
        },
    )
    result = result.to_dicts()

    assert len(result) == 5
    assert result[0]["numPersons"] == 66
    assert result[0]["city"] in ("Houston", "Birmingham")
    assert result[0]["country"] in ("United States", "United Kingdom")


def test_benchmark_query7(benchmark, connection):
    result = benchmark(
        query.run_query7,
        connection,
        {
            "country": "United States",
            "age_lower": 23,
            "age_upper": 30,
            "interest": "photography",
        },
    )
    result = result.to_dicts()

    assert len(result) == 1
    assert result[0]["numPersons"] == 150
    assert result[0]["state"] == "California"
    assert result[0]["country"] == "United States"


def test_benchmark_query8(benchmark, connection):
    result = benchmark(query.run_query8, connection)
    result = result.to_dicts()

    assert len(result) == 1
    assert result[0]["numPaths"] == 58431994


def test_benchmark_query9(benchmark, connection):
    result = benchmark(query.run_query9, connection, {"age_1": 50, "age_2": 25})
    result = result.to_dicts()

    assert len(result) == 1
    assert result[0]["numPaths"] == 45633521
