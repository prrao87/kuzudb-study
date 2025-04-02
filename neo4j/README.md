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

> [!NOTE]
> All timing numbers shown below are on an M3 Macbook Pro with 32 GB of RAM.

The script `build_graph.py` contains the necessary methods to connect to the Neo4j DB and ingest the data from the CSV files, in batches for large amounts of data.

```sh
python build_graph.py
```

## Visualize graph

You can visualize the graph in the Neo4j browser by a) downloading the Neo4j Desktop tool, or b) in the browser via `http://localhost:7474`.

## Ingestion performance

The numbers shown below are for when we ingest 100K person nodes, ~10K location nodes and ~2.
4M edges into the graph. Note the following points:

- **The goal is to perform the entire task in Python**, so we don't want to use other means like `apoc` ot `LOAD CSV` to ingest the data (which may be faster, but would require additional glue code, which defeats the purpose of this exercise)
- The [async API](https://neo4j.com/docs/api/python-driver/current/async_api.html) of the Neo4j Python client is used, which is observed on this dataset to perform ~40% faster than the sync API
- The person nodes and person-person follower edges are **ingested in batches**, which is part of the [best practices](https://neo4j.com/docs/python-manual/current/performance/) when passing data to Neo4j via Python -- this is because the number of persons and followers can get very large, causing the number of edges to nonlinearly increase with the size of the dataset.
- The batch size is set to 500K, which may seem large at first glance, but for the given data, the nodes and edges, even after `UNWIND`ing in Cypher, are small enough to fit in batch memory per transaction -- the memory requirements may be different on more complex datasets

```sh
# Set large batch size of 500k
$ python build_graph.py -b 500000

Nodes loaded in 3.5183s
Edges loaded in 41.6437s
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
┌──────────┬───────────────────┬──────────────┐
│ personID ┆ name              ┆ numFollowers │
│ ---      ┆ ---               ┆ ---          │
│ i64      ┆ str               ┆ i64          │
╞══════════╪═══════════════════╪══════════════╡
│ 85723    ┆ Melissa Murphy    ┆ 4998         │
│ 68753    ┆ Jocelyn Patterson ┆ 4985         │
│ 54696    ┆ Michael Herring   ┆ 4976         │
└──────────┴───────────────────┴──────────────┘

Query 2:
 
        MATCH (follower:Person) -[:FOLLOWS]-> (person:Person)
        WITH person, count(follower) as followers
        ORDER BY followers DESC LIMIT 1
        MATCH (person) -[:LIVES_IN]-> (city:City)
        RETURN person.name AS name, followers AS numFollowers, city.city AS city, city.state AS state, city.country AS country
    
City in which most-followed person lives:
shape: (1, 5)
┌────────────────┬──────────────┬────────┬───────┬───────────────┐
│ name           ┆ numFollowers ┆ city   ┆ state ┆ country       │
│ ---            ┆ ---          ┆ ---    ┆ ---   ┆ ---           │
│ str            ┆ i64          ┆ str    ┆ str   ┆ str           │
╞════════════════╪══════════════╪════════╪═══════╪═══════════════╡
│ Melissa Murphy ┆ 4998         ┆ Austin ┆ Texas ┆ United States │
└────────────────┴──────────────┴────────┴───────┴───────────────┘

Query 3:
 
        MATCH (p:Person) -[:LIVES_IN]-> (c:City) -[*1..2]-> (co:Country)
        WHERE co.country = $country
        RETURN c.city AS city, avg(p.age) AS averageAge
        ORDER BY averageAge LIMIT 5
    
Cities with lowest average age in United States:
shape: (5, 2)
┌─────────────┬────────────┐
│ city        ┆ averageAge │
│ ---         ┆ ---        │
│ str         ┆ f64        │
╞═════════════╪════════════╡
│ Austin      ┆ 38.780347  │
│ Kansas City ┆ 38.885064  │
│ Miami       ┆ 38.903869  │
│ San Antonio ┆ 38.950311  │
│ Houston     ┆ 38.953125  │
└─────────────┴────────────┘

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
│ United States  ┆ 30680        │
│ Canada         ┆ 3045         │
│ United Kingdom ┆ 1801         │
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
│ 141        ┆ California ┆ United States │
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
│ 45578816 │
└──────────┘
        
Neo4j query script completed in 9.590890s
```

### Query performance benchmark

The benchmark is run using `pytest-benchmark` package as follows.

```sh
$ pytest benchmark_query.py --benchmark-min-rounds=5 --benchmark-warmup-iterations=5 --benchmark-disable-gc --benchmark-sort=fullname
======================================= test session starts =======================================
platform darwin -- Python 3.13.2, pytest-8.3.5, pluggy-1.5.0
benchmark: 5.1.0 (defaults: timer=time.perf_counter disable_gc=True min_rounds=5 min_time=0.000005 max_time=1.0 calibration_precision=10 warmup=False warmup_iterations=5)
rootdir: /Users/prrao/code/kuzudb-study/neo4j
plugins: Faker-37.1.0, benchmark-5.1.0
collected 9 items                                                                                 

benchmark_query.py .........                                                                [100%]


--------------------------------------------------------------------------------- benchmark: 9 tests ---------------------------------------------------------------------------------
Name (time in s)             Min               Max              Mean            StdDev            Median               IQR            Outliers       OPS            Rounds  Iterations
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_benchmark_query1     1.6656 (245.03)   1.7915 (180.61)   1.7267 (231.02)   0.0537 (108.84)   1.7075 (232.26)   0.0904 (219.76)        2;0    0.5791 (0.00)          5           1
test_benchmark_query2     0.5971 (87.84)    0.6323 (63.74)    0.6073 (81.25)    0.0142 (28.71)    0.6020 (81.88)    0.0100 (24.26)         1;1    1.6466 (0.01)          5           1
test_benchmark_query3     0.0342 (5.04)     0.0458 (4.61)     0.0376 (5.03)     0.0024 (4.89)     0.0377 (5.12)     0.0024 (5.92)          5;1   26.6008 (0.20)         25           1
test_benchmark_query4     0.0374 (5.50)     0.0627 (6.32)     0.0411 (5.49)     0.0047 (9.60)     0.0397 (5.40)     0.0028 (6.74)          1;1   24.3566 (0.18)         27           1
test_benchmark_query5     0.0068 (1.0)      0.0099 (1.0)      0.0075 (1.0)      0.0005 (1.0)      0.0074 (1.0)      0.0004 (1.0)          14;7  133.7898 (1.0)          98           1
test_benchmark_query6     0.0172 (2.53)     0.0222 (2.24)     0.0194 (2.59)     0.0012 (2.38)     0.0194 (2.64)     0.0015 (3.59)         17;1   51.6263 (0.39)         46           1
test_benchmark_query7     0.1363 (20.05)    0.1399 (14.10)    0.1384 (18.51)    0.0013 (2.62)     0.1383 (18.82)    0.0021 (5.11)          2;0    7.2268 (0.05)          8           1
test_benchmark_query8     3.1932 (469.75)   3.2424 (326.87)   3.2203 (430.84)   0.0201 (40.82)    3.2165 (437.53)   0.0319 (77.49)         2;0    0.3105 (0.00)          5           1
test_benchmark_query9     3.8725 (569.69)   3.9164 (394.81)   3.8970 (521.37)   0.0166 (33.63)    3.9005 (530.58)   0.0221 (53.72)         2;0    0.2566 (0.00)          5           1
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Legend:
  Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
  OPS: Operations Per Second, computed as 1 / Mean
================================== 9 passed in 72.72s (0:01:12) ===================================
```