# Kùzu graph

This section describes how to build and query a graph of the social network data in KùzuDB. It uses Kùzu's [client API](https://github.com/kuzudb/kuzu) to perform the ingestion and querying.

> [!NOTE]
> All timing numbers shown below are on an M3 Macbook Pro with 32 GB of RAM.

## Setup

Because Kùzu is an embedded graph database, the database is tightly coupled with the application layer -- there is no server to set up and run. Simply `pip install kuzu` and you're good to go!

## Build graph

The script `build_graph.py` contains the necessary methods to connect to the KùzuDB DB and ingest the data from the CSV files, in batches for large amounts of data.

```sh
python build_graph.py --batch_size 50000
```

## Visualize graph

The provided `docker-compose.yml` allows you to run [Kùzu Explorer](https://github.com/kuzudb/explorer), an open source visualization
tool for KùzuDB. To run the Kùzu Explorer, install Docker and run the following command:

```sh
docker compose up
```

This allows you to access to visualize the graph on the browser at `http://localhost:8000`.

## Ingestion performance

The numbers shown below are for when we ingest 100K person nodes, ~10K location nodes and ~2.4M edges into the graph.

As expected, the nodes load much faster than the edges, since there are many more edges than nodes. The run times for ingesting nodes and edges are output to the console.

```bash
$ python build_graph.py
Nodes loaded in 0.1243s
Edges loaded in 0.3529s
Successfully loaded nodes and edges into KùzuDB!
```

## Query graph

The script `query.py` contains a suite of queries that can be run to benchmark various aspects of the DB's performance.

```sh
python query.py
```

### Case 1: Kùzu single-threaded

As per the [Neo4j docs](https://neo4j.com/docs/java-reference/current/transaction-management/), "transactions are single-threaded, confined, and independent". To keep a fair comparison with Neo4j, we thus limit the number of threads that Kùzu executes queries on to a single thread.

In the Python client, this is done as follows.

```py
CONNECTION.set_max_threads_for_exec(1)
```

#### Results 
```
Query 1:
 
        MATCH (follower:Person)-[:Follows]->(person:Person)
        RETURN person.id AS personID, person.name AS name, count(follower.id) AS numFollowers
        ORDER BY numFollowers DESC LIMIT 3;
    
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
 
        MATCH (follower:Person)-[:Follows]->(person:Person)
        WITH person, count(follower.id) as numFollowers
        ORDER BY numFollowers DESC LIMIT 1
        MATCH (person) -[:LivesIn]-> (city:City)
        RETURN person.name AS name, numFollowers, city.city AS city, city.state AS state, city.country AS country;
    
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
 
        MATCH (p:Person) -[:LivesIn]-> (c:City) -[*1..2]-> (co:Country)
        WHERE co.country = $country
        RETURN c.city AS city, avg(p.age) AS averageAge
        ORDER BY averageAge LIMIT 5;
    
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
 
        MATCH (p:Person)-[:LivesIn]->(ci:City)-[*1..2]->(country:Country)
        WHERE p.age >= $age_lower AND p.age <= $age_upper
        RETURN country.country AS countries, count(country) AS personCounts
        ORDER BY personCounts DESC LIMIT 3;
    
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
 
        MATCH (p:Person)-[:HasInterest]->(i:Interest)
        WHERE lower(i.interest) = lower($interest)
        AND lower(p.gender) = lower($gender)
        WITH p, i
        MATCH (p)-[:LivesIn]->(c:City)
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
 
        MATCH (p:Person)-[:HasInterest]->(i:Interest)
        WHERE lower(i.interest) = lower($interest)
        AND lower(p.gender) = lower($gender)
        WITH p, i
        MATCH (p)-[:LivesIn]->(c:City)
        RETURN count(p.id) AS numPersons, c.city AS city, c.country AS country
        ORDER BY numPersons DESC LIMIT 5
    
City with the most female users who have an interest in tennis:
shape: (5, 3)
┌────────────┬────────────┬────────────────┐
│ numPersons ┆ city       ┆ country        │
│ ---        ┆ ---        ┆ ---            │
│ i64        ┆ str        ┆ str            │
╞════════════╪════════════╪════════════════╡
│ 66         ┆ Birmingham ┆ United Kingdom │
│ 66         ┆ Houston    ┆ United States  │
│ 65         ┆ Raleigh    ┆ United States  │
│ 64         ┆ Montreal   ┆ Canada         │
│ 62         ┆ Phoenix    ┆ United States  │
└────────────┴────────────┴────────────────┘

Query 7:
 
        MATCH (p:Person)-[:LivesIn]->(:City)-[:CityIn]->(s:State)
        WHERE p.age >= $age_lower AND p.age <= $age_upper AND s.country = $country
        WITH p, s
        MATCH (p)-[:HasInterest]->(i:Interest)
        WHERE lower(i.interest) = lower($interest)
        RETURN count(p.id) AS numPersons, s.state AS state, s.country AS country
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
 
        MATCH (a:Person)-[r1:Follows]->(b:Person)-[r2:Follows]->(c:Person)
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
 
        MATCH (a:Person)-[r1:Follows]->(b:Person)-[r2:Follows]->(c:Person)
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
        
Queries completed in 0.7180s
```

#### Query performance

```sh
$ pytest benchmark_query.py --benchmark-min-rounds=5 --benchmark-warmup-iterations=5 --benchmark-disable-gc --benchmark-sort=fullname
======================================= test session starts =======================================
platform darwin -- Python 3.13.2, pytest-8.3.5, pluggy-1.5.0
benchmark: 5.1.0 (defaults: timer=time.perf_counter disable_gc=True min_rounds=5 min_time=0.000005 max_time=1.0 calibration_precision=10 warmup=False warmup_iterations=5)
rootdir: /Users/prrao/code/kuzudb-study/kuzudb
plugins: Faker-37.1.0, benchmark-5.1.0
collected 9 items                                                                                 

benchmark_query.py .........                                                                                                                                         [100%]


-------------------------------------------------------------------------------------- benchmark: 9 tests -------------------------------------------------------------------------------------
Name (time in ms)              Min                 Max                Mean            StdDev              Median                IQR            Outliers       OPS            Rounds  Iterations
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_benchmark_query1     155.8396 (19.47)    167.1695 (18.18)    160.2726 (18.85)    5.2565 (29.98)    157.4745 (18.71)     9.1448 (44.73)         1;0    6.2394 (0.05)          5           1
test_benchmark_query2     242.6972 (30.32)    259.1847 (28.18)    249.7981 (29.38)    8.0146 (45.71)    244.6717 (29.07)    14.0766 (68.86)         2;0    4.0032 (0.03)          5           1
test_benchmark_query3       8.2110 (1.03)       9.1963 (1.0)        8.5017 (1.0)      0.1753 (1.0)        8.4745 (1.01)      0.2044 (1.0)          14;3  117.6229 (1.0)          73           1
test_benchmark_query4      14.0767 (1.76)      15.9582 (1.74)      14.7405 (1.73)     0.4328 (2.47)      14.6126 (1.74)      0.5326 (2.61)         18;1   67.8403 (0.58)         57           1
test_benchmark_query5      12.7542 (1.59)      14.2468 (1.55)      13.4338 (1.58)     0.2857 (1.63)      13.3997 (1.59)      0.3623 (1.77)         12;2   74.4390 (0.63)         57           1
test_benchmark_query6      34.7106 (4.34)      41.0924 (4.47)      36.1866 (4.26)     1.3904 (7.93)      35.8769 (4.26)      1.1814 (5.78)          3;2   27.6346 (0.23)         27           1
test_benchmark_query7      14.3291 (1.79)      17.9396 (1.95)      15.0539 (1.77)     0.5922 (3.38)      14.9225 (1.77)      0.3682 (1.80)          6;4   66.4280 (0.56)         57           1
test_benchmark_query8       8.0038 (1.0)       20.3776 (2.22)       8.6039 (1.01)     1.2751 (7.27)       8.4171 (1.0)       0.3195 (1.56)          2;5  116.2262 (0.99)        105           1
test_benchmark_query9      91.1541 (11.39)    101.9540 (11.09)     95.5446 (11.24)    4.0400 (23.04)     94.0344 (11.17)     7.2876 (35.65)         4;0   10.4663 (0.09)         10           1
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Legend:
  Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
  OPS: Operations Per Second, computed as 1 / Mean
============================================================================ 9 passed in 10.54s ============================================================================
```
