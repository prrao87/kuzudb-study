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
        
Neo4j query script completed in 11.379769s
```

### Query performance benchmark

The benchmark is run using `pytest-benchmark` package as follows.

```sh
$ pytest benchmark_query.py --benchmark-min-rounds=5 --benchmark-warmup-iterations=5 --benchmark-disable-gc --benchmark-sort=fullname

======================================= test session starts =======================================
platform darwin -- Python 3.11.2, pytest-7.4.0, pluggy-1.2.0
benchmark: 4.0.0 (defaults: timer=time.perf_counter disable_gc=True min_rounds=5 min_time=0.000005 max_time=1.0 calibration_precision=10 warmup=False warmup_iterations=5)
rootdir: /code/kuzudb-study/neo4j
plugins: Faker-19.2.0, anyio-3.7.1, benchmark-4.0.0
collected 9 items                                                                                 

benchmark_query.py .........                                                                [100%]


--------------------------------------------------------------------------------- benchmark: 9 tests ---------------------------------------------------------------------------------
Name (time in s)             Min               Max              Mean            StdDev            Median               IQR            Outliers       OPS            Rounds  Iterations
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_benchmark_query1     1.7236 (255.00)   2.0760 (139.37)   1.8899 (219.44)   0.1629 (104.86)   1.8429 (220.10)   0.3035 (192.28)        2;0    0.5291 (0.00)          5           1
test_benchmark_query2     0.6652 (98.42)    0.7665 (51.46)    0.6936 (80.54)    0.0414 (26.64)    0.6793 (81.13)    0.0345 (21.87)         1;1    1.4417 (0.01)          5           1
test_benchmark_query3     0.0393 (5.82)     0.0554 (3.72)     0.0442 (5.13)     0.0040 (2.58)     0.0433 (5.18)     0.0056 (3.52)          4;1   22.6124 (0.19)         21           1
test_benchmark_query4     0.0401 (5.94)     0.0586 (3.93)     0.0473 (5.49)     0.0057 (3.66)     0.0467 (5.57)     0.0078 (4.92)          6;0   21.1450 (0.18)         20           1
test_benchmark_query5     0.0068 (1.0)      0.0149 (1.0)      0.0086 (1.0)      0.0016 (1.0)      0.0084 (1.0)      0.0017 (1.11)         18;3  116.1125 (1.0)          84           1
test_benchmark_query6     0.0190 (2.81)     0.0259 (1.74)     0.0226 (2.63)     0.0017 (1.12)     0.0235 (2.80)     0.0029 (1.82)         11;0   44.1985 (0.38)         39           1
test_benchmark_query7     0.1598 (23.64)    0.1732 (11.63)    0.1625 (18.87)    0.0048 (3.07)     0.1611 (19.24)    0.0016 (1.0)           1;1    6.1527 (0.05)          7           1
test_benchmark_query8     3.3745 (499.25)   3.6049 (242.01)   3.4529 (400.92)   0.0902 (58.08)    3.4238 (408.91)   0.0982 (62.21)         1;0    0.2896 (0.00)          5           1
test_benchmark_query9     4.1293 (610.91)   4.4225 (296.90)   4.2707 (495.88)   0.1211 (78.00)    4.3100 (514.74)   0.1937 (122.72)        2;0    0.2342 (0.00)          5           1
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Legend:
  Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
  OPS: Operations Per Second, computed as 1 / Mean
================================== 9 passed in 79.20s (0:01:19) ===================================

```