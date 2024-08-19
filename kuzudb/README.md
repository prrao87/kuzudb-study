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
dockercompose up
```

This allows you to access to visualize the graph on the browser at `http://localhost:8000`.

## Ingestion performance

The numbers shown below are for when we ingest 100K person nodes, ~10K location nodes and ~2.4M edges into the graph.

As expected, the nodes load much faster than the edges, since there are many more edges than nodes. The run times for ingesting nodes and edges are output to the console.

```bash
$ python build_graph.py
Nodes loaded in 0.1542s
Edges loaded in 0.3803s
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
│ Austin      ┆ 37.732948  │
│ Kansas City ┆ 37.83065   │
│ Miami       ┆ 37.860339  │
│ Houston     ┆ 37.894676  │
│ San Antonio ┆ 37.896669  │
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
│ United States  ┆ 30698        │
│ Canada         ┆ 3037         │
│ United Kingdom ┆ 1819         │
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
│ 66         ┆ Houston    ┆ United States  │
│ 66         ┆ Birmingham ┆ United Kingdom │
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
│ 165        ┆ California ┆ United States │
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
│ 46061065 │
└──────────┘
        
Queries completed in 0.9352s
```

#### Query performance benchmark (Kùzu single-threaded)

The benchmark is run using `pytest-benchmark` package as follows.

```sh
$ pytest benchmark_query.py --benchmark-min-rounds=5 --benchmark-warmup-iterations=5 --benchmark-disable-gc --benchmark-sort=fullname
================================================================================================== test session starts ==================================================================================================
platform darwin -- Python 3.12.4, pytest-8.3.2, pluggy-1.5.0
benchmark: 4.0.0 (defaults: timer=time.perf_counter disable_gc=True min_rounds=5 min_time=0.000005 max_time=1.0 calibration_precision=10 warmup=False warmup_iterations=5)
rootdir: /Users/prrao/code/kuzudb-study/kuzudb
plugins: benchmark-4.0.0, Faker-27.0.0
collected 9 items                                                                                                                                                                                                       

benchmark_query.py .........                                                                                                                                                                                      [100%]


-------------------------------------------------------------------------------------- benchmark: 9 tests -------------------------------------------------------------------------------------
Name (time in ms)              Min                 Max                Mean            StdDev              Median                IQR            Outliers       OPS            Rounds  Iterations
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_benchmark_query1     209.0226 (37.48)    225.0497 (29.72)    215.5997 (34.97)    5.8951 (13.21)    215.0382 (35.75)     5.9799 (20.00)         2;0    4.6382 (0.03)          5           1
test_benchmark_query2     246.2083 (44.15)    264.1887 (34.89)    252.6910 (40.98)    7.4496 (16.69)    249.8977 (41.55)    10.9899 (36.76)         1;0    3.9574 (0.02)          5           1
test_benchmark_query3       7.8650 (1.41)      10.3009 (1.36)       8.4119 (1.36)     0.5128 (1.15)       8.2522 (1.37)      0.2990 (1.0)          10;9  118.8793 (0.73)         77           1
test_benchmark_query4       5.5767 (1.0)        7.5731 (1.0)        6.1661 (1.0)      0.4463 (1.0)        6.0145 (1.0)       0.5087 (1.70)         28;6  162.1773 (1.0)         110           1
test_benchmark_query5      17.1654 (3.08)      19.9440 (2.63)      18.1153 (2.94)     0.5701 (1.28)      18.0157 (3.00)      0.5536 (1.85)         12;2   55.2021 (0.34)         43           1
test_benchmark_query6      57.9529 (10.39)     61.3611 (8.10)      59.7041 (9.68)     1.0348 (2.32)      59.7962 (9.94)      1.7159 (5.74)          6;0   16.7493 (0.10)         17           1
test_benchmark_query7      11.9360 (2.14)      14.5519 (1.92)      12.8594 (2.09)     0.4884 (1.09)      12.8518 (2.14)      0.5965 (2.00)         19;1   77.7638 (0.48)         61           1
test_benchmark_query8      61.0895 (10.95)     79.2555 (10.47)     63.8552 (10.36)    4.3809 (9.82)      62.7752 (10.44)     1.2777 (4.27)          1;1   15.6604 (0.10)         15           1
test_benchmark_query9     166.9417 (29.94)    172.1303 (22.73)    169.9383 (27.56)    1.9027 (4.26)     170.3806 (28.33)     2.4920 (8.34)          2;0    5.8845 (0.04)          6           1
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Legend:
  Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
  OPS: Operations Per Second, computed as 1 / Mean
================================================================================================== 9 passed in 11.21s ===================================================================================================
```

#### Query performance (Kùzu multi-threaded)

```sh
$ pytest benchmark_query.py --benchmark-min-rounds=5 --benchmark-warmup-iterations=5 --benchmark-disable-gc --benchmark-sort=fullname
================================================================================================== test session starts ==================================================================================================
platform darwin -- Python 3.12.4, pytest-8.3.2, pluggy-1.5.0
benchmark: 4.0.0 (defaults: timer=time.perf_counter disable_gc=True min_rounds=5 min_time=0.000005 max_time=1.0 calibration_precision=10 warmup=False warmup_iterations=5)
rootdir: /Users/prrao/code/kuzudb-study/kuzudb
plugins: benchmark-4.0.0, Faker-27.0.0
collected 9 items                                                                                                                                                                                                       

benchmark_query.py .........                                                                                                                                                                                      [100%]


-------------------------------------------------------------------------------------- benchmark: 9 tests --------------------------------------------------------------------------------------
Name (time in ms)              Min                 Max                Mean             StdDev              Median                IQR            Outliers       OPS            Rounds  Iterations
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_benchmark_query1     231.0743 (32.50)    261.8040 (21.24)    250.8162 (30.15)    12.6695 (28.81)    257.7072 (31.81)    17.3084 (38.99)         1;0    3.9870 (0.03)          5           1
test_benchmark_query2     273.6126 (38.48)    297.1214 (24.10)    282.6447 (33.97)     8.9920 (20.45)    279.3069 (34.48)    10.4895 (23.63)         2;0    3.5380 (0.03)          5           1
test_benchmark_query3       9.9735 (1.40)      12.3276 (1.0)       11.0040 (1.32)      0.4398 (1.0)       11.0476 (1.36)      0.4770 (1.07)         21;3   90.8758 (0.76)         65           1
test_benchmark_query4       7.1110 (1.0)       17.2494 (1.40)       8.3197 (1.0)       1.3347 (3.03)       8.1007 (1.0)       0.6346 (1.43)          4;4  120.1966 (1.0)          87           1
test_benchmark_query5      16.3182 (2.29)      18.7523 (1.52)      17.3595 (2.09)      0.4974 (1.13)      17.3593 (2.14)      0.6131 (1.38)         11;1   57.6053 (0.48)         45           1
test_benchmark_query6      58.4198 (8.22)      64.1914 (5.21)      60.5753 (7.28)      1.6598 (3.77)      60.5213 (7.47)      2.5499 (5.74)          4;0   16.5084 (0.14)         17           1
test_benchmark_query7      12.5706 (1.77)      15.4372 (1.25)      13.6218 (1.64)      0.4853 (1.10)      13.5676 (1.67)      0.4439 (1.0)          14;4   73.4115 (0.61)         60           1
test_benchmark_query8      60.2927 (8.48)      67.3211 (5.46)      64.2639 (7.72)      2.1083 (4.79)      64.5842 (7.97)      2.6848 (6.05)          5;0   15.5608 (0.13)         15           1
test_benchmark_query9     134.8778 (18.97)    150.1560 (12.18)    141.7584 (17.04)     5.0156 (11.40)    141.7625 (17.50)     5.8772 (13.24)         2;0    7.0543 (0.06)          7           1
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Legend:
  Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
  OPS: Operations Per Second, computed as 1 / Mean
================================================================================================== 9 passed in 11.99s ===================================================================================================
```
