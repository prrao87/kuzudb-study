# Neo4j graph

This section describes how to build and query a graph of the social network data in Neo4j. It uses the official `neo4j` [Python client](https://github.com/neo4j/neo4j-python-driver) to perform the ingestion and querying.

## Run Neo4j in a Docker container

Because Neo4j uses a client-server architecture, for development purposes, it makes sense to use Docker to orchestrate the setup and teardown of the DB. This is done easily via `docker-compose` as follows.

### Create a `.env` file with DB credentials

The necessary authentication to the database is specified via the variables in `.env.example`. Copy this example file, rename it to `.env` and update the `NEO4J_PASSWORD` field with the desired DB password.

Then, run the Docker container in detached mode as follows.

```sh
docker compose up -d
```

Once development and querying are finished, the container can be stopped as follows.

```sh
docker compose down
```

## Build graph

The script `build_graph.py` contains the necessary methods to connect to the Neo4j DB and ingest the data from the CSV files, in batches for large amounts of data.

```sh
python build_graph.py --batch_size 50000
```

### Ingestion performance

The numbers shown below are for when we ingest 100K person nodes, ~10K location nodes and ~2.
4M edges into the graph. Note the following points:

> 💡 The timing numbers shown below are on an M2 Macbook Pro with 16 GB of RAM.

- **The goal is to perform the entire task in Python**, so we don't want to use other means like `apoc` ot `LOAD CSV` to ingest the data (which may be faster, but would require additional glue code, which defeats the purpose of this exercise)
- The [async API](https://neo4j.com/docs/api/python-driver/current/async_api.html) of the Neo4j Python client is used, which is observed on this dataset to perform ~40% faster than the sync API
- The person nodes and person-person follower edges are **ingested in batches**, which is part of the [best practices](https://neo4j.com/docs/python-manual/current/performance/) when passing data to Neo4j via Python -- this is because the number of persons and followers can get very large, causing the number of edges to nonlinearly increase with the size of the dataset.
- The batch size is set to 500K, which may seem large at first glance, but for the given data, the nodes and edges, even after `UNWIND`ing in Cypher, are small enough to fit in batch memory per transaction -- the memory requirements may be different on more complex datasets

```sh
# Set large batch size of 500k
$ python build_graph.py -b 500000

Nodes loaded in 2.6353s
Edges loaded in 36.1358s
```

As expected, the nodes load much faster than the edges, since there are many more edges than nodes. In addition, the nodes in Neo4j are indexed (via uniqueness constraints), following which the edges are created based on a match on existing nodes, allowing us to achieve this performance.

## Query graph

The script `query.py` contains a suite of queries that can be run to benchmark various aspects of the DB's performance.

```sh
python query.py
```

#### Output

```
Query 1:

        MATCH (follower:Person)-[:FOLLOWS]->(person:Person)
        RETURN person.personID AS personID, person.name AS name, count(follower) AS numFollowers
        ORDER BY numFollowers DESC LIMIT 3

Top 3 most-followed persons:
shape: (3, 3)
┌──────────┬────────────────┬──────────────┐
│ personID ┆ name           ┆ numFollowers │
│ ---      ┆ ---            ┆ ---          │
│ i64      ┆ str            ┆ i64          │
╞══════════╪════════════════╪══════════════╡
│ 85723    ┆ Rachel Cooper  ┆ 4998         │
│ 68753    ┆ Claudia Booker ┆ 4985         │
│ 54696    ┆ Brian Burgess  ┆ 4976         │
└──────────┴────────────────┴──────────────┘

Query 2:

        MATCH (follower:Person) -[:FOLLOWS]-> (person:Person)
        WITH person, count(follower) as followers
        ORDER BY followers DESC LIMIT 1
        MATCH (person) -[:LIVES_IN]-> (city:City)
        RETURN person.name AS name, followers AS numFollowers, city.city AS city, city.state AS state, city.country AS country

City in which most-followed person lives:
shape: (1, 5)
┌───────────────┬──────────────┬────────┬───────┬───────────────┐
│ name          ┆ numFollowers ┆ city   ┆ state ┆ country       │
│ ---           ┆ ---          ┆ ---    ┆ ---   ┆ ---           │
│ str           ┆ i64          ┆ str    ┆ str   ┆ str           │
╞═══════════════╪══════════════╪════════╪═══════╪═══════════════╡
│ Rachel Cooper ┆ 4998         ┆ Austin ┆ Texas ┆ United States │
└───────────────┴──────────────┴────────┴───────┴───────────────┘

Query 3:

        MATCH (p:Person) -[:LIVES_IN]-> (c:City) -[*1..2]-> (co:Country)
        WHERE co.country = $country
        RETURN c.city AS city, avg(p.age) AS averageAge
        ORDER BY averageAge LIMIT 5

Cities with lowest average age in United States:
shape: (5, 2)
┌───────────────┬────────────┐
│ city          ┆ averageAge │
│ ---           ┆ ---        │
│ str           ┆ f64        │
╞═══════════════╪════════════╡
│ Louisville    ┆ 37.099473  │
│ Denver        ┆ 37.202703  │
│ San Francisco ┆ 37.26213   │
│ Tampa         ┆ 37.327765  │
│ Nashville     ┆ 37.343006  │
└───────────────┴────────────┘

Query 4:

        MATCH (p:Person)-[:LIVES_IN]->(ci:City)-[*1..2]->(country:Country)
        WHERE p.age >= $age_lower AND p.age <= $age_upper
        RETURN country.country AS countries, count(country) AS personCounts
        ORDER BY personCounts DESC LIMIT 3

Persons between ages 30-40 in each country:
shape: (3, 2)
┌────────────────┬──────────────┐
│ countries      ┆ personCounts │
│ ---            ┆ ---          │
│ str            ┆ i64          │
╞════════════════╪══════════════╡
│ United States  ┆ 30473        │
│ Canada         ┆ 3064         │
│ United Kingdom ┆ 1873         │
└────────────────┴──────────────┘

Query 5:

        MATCH (p:Person)-[:HAS_INTEREST]->(i:Interest)
        WHERE tolower(i.interest) = tolower($interest)
        AND tolower(p.gender) = tolower($gender)
        WITH p, i
        MATCH (p)-[:LIVES_IN]->(c:City)
        WHERE c.city = $city AND c.country = $country
        RETURN count(p) AS numPersons

Number of male users in London, United Kingdom who have an interest in fine dining:
shape: (1, 1)
┌────────────┐
│ numPersons │
│ ---        │
│ i64        │
╞════════════╡
│ 52         │
└────────────┘

Query 6:

        MATCH (p:Person)-[:HAS_INTEREST]->(i:Interest)
        WHERE tolower(i.interest) = tolower($interest)
        AND tolower(p.gender) = tolower($gender)
        WITH p, i
        MATCH (p)-[:LIVES_IN]->(c:City)
        RETURN count(p) AS numPersons, c.city AS city, c.country AS country
        ORDER BY numPersons DESC LIMIT 5

Cities with the most female users who have an interest in tennis:
shape: (5, 3)
┌────────────┬────────────┬────────────────┐
│ numPersons ┆ city       ┆ country        │
│ ---        ┆ ---        ┆ ---            │
│ i64        ┆ str        ┆ str            │
╞════════════╪════════════╪════════════════╡
│ 66         ┆ Houston    ┆ United States  │
│ 66         ┆ Birmingham ┆ United Kingdom │
│ 65         ┆ Raleigh    ┆ United States  │
│ 64         ┆ Montreal   ┆ Canada         │
│ 62         ┆ Phoenix    ┆ United States  │
└────────────┴────────────┴────────────────┘

Query 7:

        MATCH (p:Person)-[:LIVES_IN]->(:City)-[:CITY_IN]->(s:State)
        WHERE p.age >= $age_lower AND p.age <= $age_upper AND s.country = $country
        WITH p, s
        MATCH (p)-[:HAS_INTEREST]->(i:Interest)
        WHERE tolower(i.interest) = tolower($interest)
        RETURN count(p) AS numPersons, s.state AS state, s.country AS country
        ORDER BY numPersons DESC LIMIT 1


        State in United States with the most users between ages 23-30 who have an interest in photography:
shape: (1, 3)
┌────────────┬────────────┬───────────────┐
│ numPersons ┆ state      ┆ country       │
│ ---        ┆ ---        ┆ ---           │
│ i64        ┆ str        ┆ str           │
╞════════════╪════════════╪═══════════════╡
│ 170        ┆ California ┆ United States │
└────────────┴────────────┴───────────────┘


Query 8:

        MATCH (p1:Person)-[f:FOLLOWS]->(p2:Person)
        WHERE p1.personID > p2.personID
        RETURN count(f) as numFollowers

Number of first degree connections reachable in the graph:
shape: (1, 1)
┌──────────────┐
│ numFollowers │
│ ---          │
│ i64          │
╞══════════════╡
│ 1214477      │
└──────────────┘

Query 9:

        MATCH (:Person)-[r1:FOLLOWS]->(influencer:Person)-[r2:FOLLOWS]->(:Person)
        WITH count(r1) AS numFollowers, influencer, r2
        WHERE influencer.age <= $age_upper AND numFollowers > 3000
        RETURN influencer.id AS influencerId, influencer.name AS name, count(r2) AS numFollows
        ORDER BY numFollows DESC LIMIT 5;


        Influencers below age 30 who follow the most people:
shape: (5, 3)
┌──────────────┬─────────────────┬────────────┐
│ influencerId ┆ name            ┆ numFollows │
│ ---          ┆ ---             ┆ ---        │
│ i64          ┆ str             ┆ i64        │
╞══════════════╪═════════════════╪════════════╡
│ 89758        ┆ Joshua Williams ┆ 40         │
│ 85914        ┆ Micheal Holt    ┆ 32         │
│ 8077         ┆ Ralph Floyd     ┆ 32         │
│ 1348         ┆ Brett Wright    ┆ 32         │
│ 70809        ┆ David Cooper    ┆ 31         │
└──────────────┴─────────────────┴────────────┘


Query 10:

        MATCH (:Person)-[r1:FOLLOWS]->(influencer:Person)-[r2:FOLLOWS]->(person:Person)
        WITH count(r1) AS numFollowers1, person, influencer, r2
        WHERE influencer.age >= $age_lower AND influencer.age <= $age_upper AND numFollowers1 > 3000
        RETURN count(r2) AS numFollowers2
        ORDER BY numFollowers2 DESC LIMIT 5;


        Number of people followed by influencers in the age range 18-25:
shape: (1, 1)
┌───────────────┐
│ numFollowers2 │
│ ---           │
│ i64           │
╞═══════════════╡
│ 690           │
└───────────────┘

Neo4j query script completed in 20.313278s
```

### Query performance benchmark

The benchmark is run using `pytest-benchmark` package as follows.

```sh
$ pytest benchmark_query.py --benchmark-min-rounds=5 --benchmark-warmup-iterations=5 --benchmark-disable-gc --benchmark-sort=fullname
================================================= test session starts ==================================================
platform darwin -- Python 3.11.2, pytest-7.4.0, pluggy-1.2.0
benchmark: 4.0.0 (defaults: timer=time.perf_counter disable_gc=True min_rounds=5 min_time=0.000005 max_time=1.0 calibration_precision=10 warmup=False warmup_iterations=5)
rootdir: /code/kuzudb-study/neo4j
plugins: Faker-19.2.0, anyio-3.7.1, benchmark-4.0.0
collected 10 items

benchmark_query.py ..........                                                                                    [100%]


--------------------------------------------------------------------------------- benchmark: 10 tests ---------------------------------------------------------------------------------
Name (time in s)              Min               Max              Mean            StdDev            Median               IQR            Outliers       OPS            Rounds  Iterations
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_benchmark_query1      1.7685 (252.71)   2.0853 (145.03)   1.8578 (221.68)   0.1292 (114.35)   1.8186 (224.85)   0.1059 (107.66)        1;1    0.5383 (0.00)          5           1
test_benchmark_query10     8.6340 (>1000.0)  8.9443 (622.06)   8.7908 (>1000.0)  0.1103 (97.55)    8.7834 (>1000.0)  0.0985 (100.09)        2;0    0.1138 (0.00)          5           1
test_benchmark_query2      0.6305 (90.09)    0.6483 (45.09)    0.6384 (76.17)    0.0074 (6.57)     0.6386 (78.95)    0.0125 (12.73)         2;0    1.5665 (0.01)          5           1
test_benchmark_query3      0.0380 (5.43)     0.0480 (3.34)     0.0405 (4.83)     0.0029 (2.52)     0.0395 (4.88)     0.0023 (2.37)          4;4   24.7145 (0.21)         22           1
test_benchmark_query4      0.0419 (5.98)     0.0624 (4.34)     0.0471 (5.62)     0.0051 (4.54)     0.0453 (5.61)     0.0053 (5.34)          5;2   21.2382 (0.18)         23           1
test_benchmark_query5      0.0070 (1.0)      0.0144 (1.0)      0.0084 (1.0)      0.0011 (1.0)      0.0081 (1.0)      0.0010 (1.0)          11;6  119.3207 (1.0)          87           1
test_benchmark_query6      0.0200 (2.86)     0.0268 (1.86)     0.0218 (2.60)     0.0015 (1.32)     0.0214 (2.64)     0.0013 (1.36)          8;5   45.8986 (0.38)         42           1
test_benchmark_query7      0.1595 (22.79)    0.1753 (12.19)    0.1634 (19.50)    0.0055 (4.85)     0.1613 (19.95)    0.0034 (3.45)          1;1    6.1194 (0.05)          7           1
test_benchmark_query8      0.8537 (122.00)   0.8821 (61.35)    0.8726 (104.12)   0.0112 (9.92)     0.8737 (108.02)   0.0119 (12.06)         1;0    1.1460 (0.01)          5           1
test_benchmark_query9      7.5164 (>1000.0)  8.3269 (579.12)   7.9377 (947.13)   0.3325 (294.18)   7.8846 (974.85)   0.5492 (558.27)        2;0    0.1260 (0.00)          5           1
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Legend:
  Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
  OPS: Operations Per Second, computed as 1 / Mean
============================================ 10 passed in 147.13s (0:02:27) ============================================

```