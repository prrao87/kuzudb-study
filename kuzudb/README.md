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
$ python build_graph.py 

Nodes loaded in 0.0578s
Edges loaded in 2.0335s
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
====================================== test session starts =======================================
platform darwin -- Python 3.11.2, pytest-7.4.0, pluggy-1.2.0
benchmark: 4.0.0 (defaults: timer=time.perf_counter disable_gc=True min_rounds=5 min_time=0.000005 max_time=1.0 calibration_precision=10 warmup=False warmup_iterations=5)
rootdir: /code/kuzudb-study/kuzudb
plugins: Faker-19.2.0, anyio-3.7.1, benchmark-4.0.0
collected 10 items                                                                               

benchmark_query.py ..........                                                              [100%]


-------------------------------------------------------------------------------------- benchmark: 10 tests --------------------------------------------------------------------------------------
Name (time in ms)               Min                 Max                Mean             StdDev              Median                IQR            Outliers       OPS            Rounds  Iterations
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_benchmark_query1      204.5318 (47.91)    264.5275 (37.83)    227.5650 (47.82)    24.9057 (78.87)    220.8040 (47.48)    39.0229 (167.82)        1;0    4.3943 (0.02)          5           1
test_benchmark_query10     781.3306 (183.02)   801.5248 (114.61)   789.4154 (165.87)    8.1112 (25.69)    789.5400 (169.76)   11.9668 (51.47)         1;0    1.2668 (0.01)          5           1
test_benchmark_query2      237.0291 (55.52)    253.8298 (36.30)    243.3142 (51.13)     6.3798 (20.20)    241.2695 (51.88)     6.8318 (29.38)         1;0    4.1099 (0.02)          5           1
test_benchmark_query3        8.5850 (2.01)      10.6163 (1.52)       9.7056 (2.04)      0.3943 (1.25)       9.7931 (2.11)      0.4372 (1.88)         25;4  103.0336 (0.49)         76           1
test_benchmark_query4        8.6458 (2.03)      10.8680 (1.55)       9.2325 (1.94)      0.5057 (1.60)       9.0836 (1.95)      0.6175 (2.66)         22;1  108.3130 (0.52)         74           1
test_benchmark_query5        4.2691 (1.0)        6.9932 (1.0)        4.7592 (1.0)       0.4073 (1.29)       4.6508 (1.0)       0.6067 (2.61)         11;1  210.1198 (1.0)          81           1
test_benchmark_query6       27.7651 (6.50)      31.7360 (4.54)      29.8077 (6.26)      0.9314 (2.95)      29.8461 (6.42)      1.0849 (4.67)          8;0   33.5484 (0.16)         33           1
test_benchmark_query7        6.9663 (1.63)       8.5708 (1.23)       7.7759 (1.63)      0.3158 (1.0)        7.7834 (1.67)      0.2325 (1.0)         18;14  128.6021 (0.61)         85           1
test_benchmark_query8      100.7867 (23.61)    110.9126 (15.86)    103.9609 (21.84)     2.9900 (9.47)     103.4902 (22.25)     1.8488 (7.95)          3;2    9.6190 (0.05)         10           1
test_benchmark_query9      853.4369 (199.91)   867.1944 (124.00)   859.6641 (180.63)    6.7229 (21.29)    856.5395 (184.17)   12.5563 (54.00)         2;0    1.1632 (0.01)          5           1
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Legend:
  Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
  OPS: Operations Per Second, computed as 1 / Mean
====================================== 10 passed in 20.95s =======================================
```

#### Query performance (Kùzu multi-threaded)

```sh
$ pytest benchmark_query.py --benchmark-min-rounds=5 --benchmark-warmup-iterations=5 --benchmark-disable-gc --benchmark-sort=fullname
====================================== test session starts =======================================
platform darwin -- Python 3.11.2, pytest-7.4.0, pluggy-1.2.0
benchmark: 4.0.0 (defaults: timer=time.perf_counter disable_gc=True min_rounds=5 min_time=0.000005 max_time=1.0 calibration_precision=10 warmup=False warmup_iterations=5)
rootdir: /code/kuzudb-study/kuzudb
plugins: Faker-19.2.0, anyio-3.7.1, benchmark-4.0.0
collected 10 items                                                                               

benchmark_query.py ..........                                                              [100%]


-------------------------------------------------------------------------------------- benchmark: 10 tests --------------------------------------------------------------------------------------
Name (time in ms)               Min                 Max                Mean             StdDev              Median                IQR            Outliers       OPS            Rounds  Iterations
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_benchmark_query1      112.0785 (27.29)    217.2179 (36.61)    136.1030 (27.11)    45.5192 (136.94)   115.3392 (23.11)    33.0138 (106.23)        1;1    7.3474 (0.04)          5           1
test_benchmark_query10     531.5120 (129.40)   557.1382 (93.90)    546.0965 (108.79)   10.4145 (31.33)    547.9619 (109.79)   16.7082 (53.76)         2;0    1.8312 (0.01)          5           1
test_benchmark_query2      120.3370 (29.30)    132.8606 (22.39)    125.9788 (25.10)     4.2911 (12.91)    125.2396 (25.09)     5.7256 (18.42)         3;0    7.9378 (0.04)          7           1
test_benchmark_query3        6.4401 (1.57)       8.0799 (1.36)       7.2587 (1.45)      0.3847 (1.16)       7.2864 (1.46)      0.5087 (1.64)         30;0  137.7665 (0.69)         78           1
test_benchmark_query4        7.0398 (1.71)       9.8535 (1.66)       8.0971 (1.61)      0.4228 (1.27)       8.0239 (1.61)      0.5342 (1.72)         23;1  123.5016 (0.62)         87           1
test_benchmark_query5        4.1076 (1.0)        5.9335 (1.0)        5.0197 (1.0)       0.3324 (1.0)        4.9908 (1.0)       0.3108 (1.0)          17;9  199.2147 (1.0)          79           1
test_benchmark_query6       11.4065 (2.78)      13.9336 (2.35)      12.4106 (2.47)      0.5122 (1.54)      12.3276 (2.47)      0.5818 (1.87)         20;2   80.5766 (0.40)         72           1
test_benchmark_query7        5.9218 (1.44)       9.0174 (1.52)       6.6288 (1.32)      0.4273 (1.29)       6.5931 (1.32)      0.4345 (1.40)         30;1  150.8580 (0.76)        104           1
test_benchmark_query8       22.5029 (5.48)      27.1075 (4.57)      23.6917 (4.72)      0.9087 (2.73)      23.4097 (4.69)      0.9917 (3.19)         10;1   42.2088 (0.21)         41           1
test_benchmark_query9      565.3163 (137.63)   578.1635 (97.44)    569.8440 (113.52)    5.5017 (16.55)    567.1719 (113.64)    8.3636 (26.91)         1;0    1.7549 (0.01)          5           1
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Legend:
  Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
  OPS: Operations Per Second, computed as 1 / Mean
====================================== 10 passed in 15.52s =======================================
```

