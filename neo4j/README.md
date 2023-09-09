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
 
        MATCH (a:Person)-[r1:FOLLOWS]->(b:Person)-[r2:FOLLOWS]->(c:Person)
        RETURN count(*) AS numPaths
    

        Number of second-degree paths:
shape: (1, 1)
┌──────────┐
│ numPaths │
│ ---      │
│ i64      │
╞══════════╡
│ 58431994 │
└──────────┘
        

Query 9:
 
        MATCH (a:Person)-[r1:FOLLOWS]->(b:Person)-[r2:FOLLOWS]->(c:Person)
        WHERE b.age < $age_1 AND c.age > $age_2
        RETURN count(*) as numPaths
    

        Number of paths through persons below 50 to persons above 25:
shape: (1, 1)
┌──────────┐
│ numPaths │
│ ---      │
│ i64      │
╞══════════╡
│ 45632026 │
└──────────┘
        
Neo4j query script completed in 13.368711s
```

### Query performance benchmark

The benchmark is run using `pytest-benchmark` package as follows.

```sh
$ pytest benchmark_query.py --benchmark-min-rounds=5 --benchmark-warmup-iterations=5 --benchmark-disable-gc --benchmark-sort=fullname

=========================================================== test session starts ============================================================
platform darwin -- Python 3.11.2, pytest-7.4.0, pluggy-1.2.0
benchmark: 4.0.0 (defaults: timer=time.perf_counter disable_gc=True min_rounds=5 min_time=0.000005 max_time=1.0 calibration_precision=10 warmup=False warmup_iterations=5)
rootdir: /code/kuzudb-study/neo4j
plugins: Faker-19.2.0, anyio-3.7.1, benchmark-4.0.0
collected 9 items                                                                                                                          

benchmark_query.py .........                                                                                                         [100%]


--------------------------------------------------------------------------------- benchmark: 9 tests ---------------------------------------------------------------------------------
Name (time in s)             Min               Max              Mean            StdDev            Median               IQR            Outliers       OPS            Rounds  Iterations
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_benchmark_query1     1.5733 (253.20)   1.6033 (63.31)    1.5928 (215.76)   0.0131 (7.05)     1.6004 (227.62)   0.0201 (41.80)         1;0    0.6278 (0.00)          5           1
test_benchmark_query2     0.5663 (91.13)    0.5889 (23.26)    0.5770 (78.17)    0.0095 (5.12)     0.5746 (81.72)    0.0163 (33.91)         2;0    1.7331 (0.01)          5           1
test_benchmark_query3     0.0362 (5.83)     0.0527 (2.08)     0.0394 (5.34)     0.0043 (2.33)     0.0376 (5.34)     0.0040 (8.33)          2;2   25.3731 (0.19)         19           1
test_benchmark_query4     0.0410 (6.60)     0.0566 (2.24)     0.0435 (5.89)     0.0032 (1.72)     0.0425 (6.04)     0.0016 (3.42)          2;2   23.0038 (0.17)         23           1
test_benchmark_query5     0.0062 (1.0)      0.0267 (1.05)     0.0074 (1.0)      0.0021 (1.15)     0.0070 (1.0)      0.0005 (1.0)           1;5  135.4661 (1.0)          88           1
test_benchmark_query6     0.0177 (2.84)     0.0253 (1.0)      0.0197 (2.67)     0.0019 (1.0)      0.0192 (2.73)     0.0014 (2.81)          7;5   50.6911 (0.37)         45           1
test_benchmark_query7     0.1517 (24.41)    0.1685 (6.66)     0.1556 (21.07)    0.0058 (3.11)     0.1538 (21.87)    0.0007 (1.46)          1;2    6.4286 (0.05)          7           1
test_benchmark_query8     3.1052 (499.72)   3.1835 (125.71)   3.1393 (425.27)   0.0333 (17.89)    3.1493 (447.93)   0.0535 (111.43)        2;0    0.3185 (0.00)          5           1
test_benchmark_query9     7.6747 (>1000.0)  7.7181 (304.78)   7.7004 (>1000.0)  0.0164 (8.82)     7.7041 (>1000.0)  0.0205 (42.60)         2;0    0.1299 (0.00)          5           1
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Legend:
  Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
  OPS: Operations Per Second, computed as 1 / Mean
======================================================= 9 passed in 97.45s (0:01:37) =======================================================

```