# Kùzu graph

This section describes how to build and query a graph of the social network data in KùzuDB. It uses Kùzu's [client API](https://github.com/kuzudb/kuzu) to perform the ingestion and querying.

## Setup

Because Kùzu is an embedded graph database, the database is tightly coupled with the application layer -- there is no server to set up and run. Simply `pip install kuzu` and you're good to go!

## Build graph

The script `build_graph.py` contains the necessary methods to connect to the KùzuDB DB and ingest the data from the CSV files, in batches for large amounts of data.

```sh
python build_graph.py --batch_size 50000
```

### Ingestion performance

The numbers shown below are for when we ingest 100K person nodes, ~10K location nodes and ~2.4M edges into the graph.

As expected, the nodes load much faster than the edges, since there are many more edges than nodes. The run times for ingesting nodes and edges are output to the console.

```
Nodes loaded in 0.0874s
Edges loaded in 2.1622s
Successfully loaded nodes and edges into KùzuDB!
```

> 💡 The timing shown is on an M2 Macbook Pro with 16 GB of RAM.

## Query graph

To verify that the graph was built correctly, the script `query.py` contains a few example queries that can be run against the DB, generating some simple statistics.

```sh
python query.py
```

The following questions are asked of the graph:

* **Query 1**: Who are the top 3 most-followed persons?
* **Query 2**: In which city does the most-followed person live?
* **Query 3**: What are the top 5 cities with the lowest average age of persons?
* **Query 4**: How many persons between ages 30-40 are there in each country?
* **Query 5**: How many men in London, United Kingdom have an interest in fine dining?
* **Query 6**: Which city has the maximum number of women that like Tennis?
* **Query 7**: Which U.S. state has the maximum number of persons between the age 23-30 who enjoy photography?
* **Query 8**: How many second degree connections are reachable in the graph?

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
┌──────────┬────────────────┬──────────────┐
│ personID ┆ name           ┆ numFollowers │
│ ---      ┆ ---            ┆ ---          │
│ i64      ┆ str            ┆ i64          │
╞══════════╪════════════════╪══════════════╡
│ 85723    ┆ Rachel Cooper  ┆ 4998         │
│ 68753    ┆ Claudia Booker ┆ 4985         │
│ 54696    ┆ Brian Burgess  ┆ 4976         │
└──────────┴────────────────┴──────────────┘
Query 1 completed in 0.311524s

Query 2:
 
        MATCH (follower:Person)-[:Follows]->(person:Person)
        WITH person, count(follower.id) as numFollowers
        ORDER BY numFollowers DESC LIMIT 1
        MATCH (person) -[:LivesIn]-> (city:City)
        RETURN person.name AS name, numFollowers, city.city AS city, city.state AS state, city.country AS country;
    
City in which most-followed person lives:
shape: (1, 5)
┌───────────────┬──────────────┬────────┬───────┬───────────────┐
│ name          ┆ numFollowers ┆ city   ┆ state ┆ country       │
│ ---           ┆ ---          ┆ ---    ┆ ---   ┆ ---           │
│ str           ┆ i64          ┆ str    ┆ str   ┆ str           │
╞═══════════════╪══════════════╪════════╪═══════╪═══════════════╡
│ Rachel Cooper ┆ 4998         ┆ Austin ┆ Texas ┆ United States │
└───────────────┴──────────────┴────────┴───────┴───────────────┘
Query 2 completed in 0.791726s

Query 3:
 
        MATCH (p:Person) -[:LivesIn]-> (c:City)-[*1..2]-> (co:Country {country: $country})
        RETURN c.city AS city, avg(p.age) AS averageAge
        ORDER BY averageAge LIMIT 5;
    
Cities with lowest average age in Canada:
shape: (5, 2)
┌───────────┬────────────┐
│ city      ┆ averageAge │
│ ---       ┆ ---        │
│ str       ┆ f64        │
╞═══════════╪════════════╡
│ Montreal  ┆ 37.328018  │
│ Calgary   ┆ 37.607205  │
│ Toronto   ┆ 37.720255  │
│ Edmonton  ┆ 37.943678  │
│ Vancouver ┆ 38.023227  │
└───────────┴────────────┘
Query 3 completed in 0.012013s

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
│ United States  ┆ 30473        │
│ Canada         ┆ 3064         │
│ United Kingdom ┆ 1873         │
└────────────────┴──────────────┘
Query 4 completed in 0.015932s

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
Query 5 completed in 0.012567s

Query 6:
 
        MATCH (p:Person)-[:HasInterest]->(i:Interest)
        WHERE lower(i.interest) = lower($interest)
        AND lower(p.gender) = lower($gender)
        WITH p, i
        MATCH (p)-[:LivesIn]->(c:City)
        RETURN count(p.id) AS numPersons, c.city, c.country
        ORDER BY numPersons DESC LIMIT 5
    
City with the most female users who have an interest in tennis:
shape: (5, 3)
┌────────────┬────────────┬────────────────┐
│ numPersons ┆ c.city     ┆ c.country      │
│ ---        ┆ ---        ┆ ---            │
│ i64        ┆ str        ┆ str            │
╞════════════╪════════════╪════════════════╡
│ 66         ┆ Birmingham ┆ United Kingdom │
│ 66         ┆ Houston    ┆ United States  │
│ 65         ┆ Raleigh    ┆ United States  │
│ 64         ┆ Montreal   ┆ Canada         │
│ 62         ┆ Phoenix    ┆ United States  │
└────────────┴────────────┴────────────────┘
Query 6 completed in 0.033764s

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
│ 170        ┆ California ┆ United States │
└────────────┴────────────┴───────────────┘
            
Query 7 completed in 0.012508s

Query 8:
 
        MATCH (p1:Person)-[f:Follows]->(p2:Person)
        WHERE p1.id > p2.id
        RETURN count(f) as numFollowers
    
Number of second degree connections reachable in the graph:
shape: (1, 1)
┌──────────────┐
│ numFollowers │
│ ---          │
│ i64          │
╞══════════════╡
│ 1214477      │
└──────────────┘
Query 8 completed in 0.103470s
Queries completed in 1.2938s
```

#### Query performance (Kùzu single-threaded)

The numbers shown below are for when we ingest 100K person nodes, ~10K location nodes and ~2.4M edges into the graph. Query times for simple aggregation and path finding are relatively low. More advanced queries involving variable length paths will be studied later.

Summary of run times:

* Query 1: `0.311524s`
* Query 2: `0.791726s`
* Query 3: `0.012013s`
* Query 4: `0.015932s`
* Query 5: `0.012567s`
* Query 6: `0.033764s`
* Query 7: `0.012508s`
* Query 8: `0.103470s`


### Case 2: Kùzu multi-threaded

We can also let Kùzu choose the optimal number of threads to run the queries on, in a multi-threaded fashion (this is the default behaviour).


#### Results

```
Query 1:
 
        MATCH (follower:Person)-[:Follows]->(person:Person)
        RETURN person.id AS personID, person.name AS name, count(follower.id) AS numFollowers
        ORDER BY numFollowers DESC LIMIT 3;
    
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
 
        MATCH (follower:Person)-[:Follows]->(person:Person)
        WITH person, count(follower.id) as numFollowers
        ORDER BY numFollowers DESC LIMIT 1
        MATCH (person) -[:LivesIn]-> (city:City)
        RETURN person.name AS name, numFollowers, city.city AS city, city.state AS state, city.country AS country;
    
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
 
        MATCH (p:Person) -[:LivesIn]-> (c:City)-[*1..2]-> (co:Country {country: $country})
        RETURN c.city AS city, avg(p.age) AS averageAge
        ORDER BY averageAge LIMIT 5;
    
Cities with lowest average age in Canada:
shape: (5, 2)
┌───────────┬────────────┐
│ city      ┆ averageAge │
│ ---       ┆ ---        │
│ str       ┆ f64        │
╞═══════════╪════════════╡
│ Montreal  ┆ 37.328018  │
│ Calgary   ┆ 37.607205  │
│ Toronto   ┆ 37.720255  │
│ Edmonton  ┆ 37.943678  │
│ Vancouver ┆ 38.023227  │
└───────────┴────────────┘

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
│ United States  ┆ 30473        │
│ Canada         ┆ 3064         │
│ United Kingdom ┆ 1873         │
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
│ 170        ┆ California ┆ United States │
└────────────┴────────────┴───────────────┘
        

Query 8:
 
        MATCH (p1:Person)-[f:Follows]->(p2:Person)
        WHERE p1.id > p2.id
        RETURN count(f) as numFollowers
    
Number of second degree connections reachable in the graph:
shape: (1, 1)
┌──────────────┐
│ numFollowers │
│ ---          │
│ i64          │
╞══════════════╡
│ 1214477      │
└──────────────┘
Queries completed in 1.2756s
```

#### Query performance benchmark (Kùzu single-threaded)

The benchmark is run using `pytest-benchmark` package as follows.

```sh
$ pytest benchmark_query.py --benchmark-min-rounds=5 --benchmark-warmup-iterations=5 --benchmark-disable-gc --benchmark-sort=fullname
==================================================================================== test session starts =====================================================================================
platform darwin -- Python 3.11.2, pytest-7.4.0, pluggy-1.2.0
benchmark: 4.0.0 (defaults: timer=time.perf_counter disable_gc=True min_rounds=5 min_time=0.000005 max_time=1.0 calibration_precision=10 warmup=False warmup_iterations=5)
rootdir: /code/kuzudb-study/kuzudb
plugins: Faker-19.2.0, anyio-3.7.1, benchmark-4.0.0
collected 8 items

benchmark_query.py ........                                                                                                                                                            [100%]


-------------------------------------------------------------------------------------- benchmark: 8 tests --------------------------------------------------------------------------------------
Name (time in ms)              Min                 Max                Mean             StdDev              Median                IQR            Outliers       OPS            Rounds  Iterations
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_benchmark_query1     187.4783 (50.09)    208.4892 (45.44)    192.4749 (48.38)     8.9712 (54.05)    188.8628 (47.85)     5.4620 (58.77)         1;1    5.1955 (0.02)          5           1
test_benchmark_query2     651.9378 (174.18)   727.6718 (158.61)   669.7257 (168.35)   32.5196 (195.93)   656.0755 (166.22)   23.4683 (252.52)        1;1    1.4931 (0.01)          5           1
test_benchmark_query3       7.1727 (1.92)      16.3433 (3.56)       8.1793 (2.06)      1.1808 (7.11)       7.9322 (2.01)      0.4850 (5.22)          7;7  122.2596 (0.49)         78           1
test_benchmark_query4       8.5364 (2.28)      11.1066 (2.42)       9.4035 (2.36)      0.8492 (5.12)       8.9223 (2.26)      1.1856 (12.76)        12;0  106.3432 (0.42)         49           1
test_benchmark_query5       3.7428 (1.0)        4.5879 (1.0)        3.9781 (1.0)       0.1660 (1.0)        3.9471 (1.0)       0.0929 (1.0)           5;4  251.3782 (1.0)          48           1
test_benchmark_query6      25.9462 (6.93)      33.3162 (7.26)      27.7400 (6.97)      1.2350 (7.44)      27.4689 (6.96)      0.8201 (8.82)          4;4   36.0490 (0.14)         36           1
test_benchmark_query7       6.9201 (1.85)       8.6525 (1.89)       7.7988 (1.96)      0.3281 (1.98)       7.7646 (1.97)      0.1844 (1.98)        18;16  128.2242 (0.51)         69           1
test_benchmark_query8      90.1384 (24.08)    108.3035 (23.61)     93.4627 (23.49)     5.1808 (31.21)     91.7108 (23.23)     2.1502 (23.14)         1;1   10.6995 (0.04)         11           1
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Legend:
  Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
  OPS: Operations Per Second, computed as 1 / Mean
===================================================================================== 8 passed in 11.92s =====================================================================================
```

#### Query performance (Kùzu multi-threaded)

```sh
$ pytest benchmark_query.py --benchmark-min-rounds=5 --benchmark-warmup-iterations=5 --benchmark-disable-gc --benchmark-sort=fullname
==================================================================================== test session starts =====================================================================================
platform darwin -- Python 3.11.2, pytest-7.4.0, pluggy-1.2.0
benchmark: 4.0.0 (defaults: timer=time.perf_counter disable_gc=True min_rounds=5 min_time=0.000005 max_time=1.0 calibration_precision=10 warmup=False warmup_iterations=5)
rootdir: /code/kuzudb-study/kuzudb
plugins: Faker-19.2.0, anyio-3.7.1, benchmark-4.0.0
collected 8 items

benchmark_query.py ........                                                                                                                                                            [100%]


-------------------------------------------------------------------------------------- benchmark: 8 tests --------------------------------------------------------------------------------------
Name (time in ms)              Min                 Max                Mean             StdDev              Median                IQR            Outliers       OPS            Rounds  Iterations
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_benchmark_query1     112.4209 (29.98)    175.6500 (27.58)    125.5608 (25.69)    28.0081 (63.91)    112.8987 (22.96)    16.8425 (32.06)         1;1    7.9643 (0.04)          5           1
test_benchmark_query2     571.3696 (152.38)   586.1770 (92.03)    577.8111 (118.23)    5.9532 (13.58)    575.7557 (117.08)    9.1151 (17.35)         2;0    1.7307 (0.01)          5           1
test_benchmark_query3       6.4611 (1.72)       8.9117 (1.40)       7.4214 (1.52)      0.6558 (1.50)       7.4137 (1.51)      1.3337 (2.54)         48;0  134.7447 (0.66)         98           1
test_benchmark_query4       6.6348 (1.77)      10.0138 (1.57)       8.5207 (1.74)      0.5462 (1.25)       8.5367 (1.74)      0.5669 (1.08)         13;2  117.3612 (0.57)         67           1
test_benchmark_query5       3.7497 (1.0)        6.3695 (1.0)        4.8872 (1.0)       0.4716 (1.08)       4.9178 (1.0)       0.6603 (1.26)         21;1  204.6181 (1.0)          70           1
test_benchmark_query6      11.1365 (2.97)      14.3319 (2.25)      12.4077 (2.54)      0.7140 (1.63)      12.3383 (2.51)      0.7948 (1.51)         15;5   80.5951 (0.39)         61           1
test_benchmark_query7       5.8870 (1.57)       8.2347 (1.29)       6.8174 (1.39)      0.4641 (1.06)       6.7216 (1.37)      0.6434 (1.22)         32;1  146.6837 (0.72)        103           1
test_benchmark_query8      20.4635 (5.46)      22.2344 (3.49)      21.1153 (4.32)      0.4383 (1.0)       21.0030 (4.27)      0.5253 (1.0)          10;1   47.3590 (0.23)         36           1
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Legend:
  Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
  OPS: Operations Per Second, computed as 1 / Mean
===================================================================================== 8 passed in 10.22s =====================================================================================
```

