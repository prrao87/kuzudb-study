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
 
        MATCH (p:Person) -[:LivesIn]-> (c:City) -[*1..2]-> (co:Country)
        WHERE co.country = $country
        RETURN c.city AS city, avg(p.age) AS averageAge
        ORDER BY averageAge LIMIT 5;
    
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
 
        MATCH (:Person)-[r1:Follows]->(influencer:Person)-[r2:Follows]->(:Person)
        WITH count(r1) AS numFollowers, influencer, id(r2) as r2ID
        WHERE influencer.age <= $age_upper AND numFollowers > 3000
        RETURN influencer.id AS influencerId, influencer.name AS name, count(r2ID) AS numFollows
        ORDER BY numFollows DESC LIMIT 5;
    

        Influencers below age 30 who follow the most people:
shape: (5, 3)
┌──────────────┬─────────────────┬────────────┐
│ influencerId ┆ name            ┆ numFollows │
│ ---          ┆ ---             ┆ ---        │
│ i64          ┆ str             ┆ i64        │
╞══════════════╪═════════════════╪════════════╡
│ 89758        ┆ Joshua Williams ┆ 40         │
│ 1348         ┆ Brett Wright    ┆ 32         │
│ 8077         ┆ Ralph Floyd     ┆ 32         │
│ 85914        ┆ Micheal Holt    ┆ 32         │
│ 2386         ┆ Robert Graham   ┆ 31         │
└──────────────┴─────────────────┴────────────┘
        

Query 10:
 
        MATCH (:Person)-[r1:Follows]->(influencer:Person)-[r2:Follows]->(person:Person)
        WITH count(id(r1)) AS numFollowers1, person, influencer, id(r2) as r2ID
        WHERE influencer.age >= $age_lower AND influencer.age <= $age_upper AND numFollowers1 > 3000
        RETURN count(r2ID) AS numFollowers2
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
        
Queries completed in 2.3699s
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
 
        MATCH (p:Person) -[:LivesIn]-> (c:City) -[*1..2]-> (co:Country)
        WHERE co.country = $country
        RETURN c.city AS city, avg(p.age) AS averageAge
        ORDER BY averageAge LIMIT 5;
    
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

Query 9:
 
        MATCH (:Person)-[r1:Follows]->(influencer:Person)-[r2:Follows]->(:Person)
        WITH count(r1) AS numFollowers, influencer, id(r2) as r2ID
        WHERE influencer.age <= $age_upper AND numFollowers > 3000
        RETURN influencer.id AS influencerId, influencer.name AS name, count(r2ID) AS numFollows
        ORDER BY numFollows DESC LIMIT 5;
    

        Influencers below age 30 who follow the most people:
shape: (5, 3)
┌──────────────┬─────────────────┬────────────┐
│ influencerId ┆ name            ┆ numFollows │
│ ---          ┆ ---             ┆ ---        │
│ i64          ┆ str             ┆ i64        │
╞══════════════╪═════════════════╪════════════╡
│ 89758        ┆ Joshua Williams ┆ 40         │
│ 1348         ┆ Brett Wright    ┆ 32         │
│ 8077         ┆ Ralph Floyd     ┆ 32         │
│ 85914        ┆ Micheal Holt    ┆ 32         │
│ 2386         ┆ Robert Graham   ┆ 31         │
└──────────────┴─────────────────┴────────────┘
        

Query 10:
 
        MATCH (:Person)-[r1:Follows]->(influencer:Person)-[r2:Follows]->(person:Person)
        WITH count(id(r1)) AS numFollowers1, person, influencer, id(r2) as r2ID
        WHERE influencer.age >= $age_lower AND influencer.age <= $age_upper AND numFollowers1 > 3000
        RETURN count(r2ID) AS numFollowers2
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
        
Queries completed in 2.7552s
```

#### Query performance benchmark (Kùzu single-threaded)

The benchmark is run using `pytest-benchmark` package as follows.

```sh
$ pytest benchmark_query.py --benchmark-min-rounds=5 --benchmark-warmup-iterations=5 --benchmark-disable-gc --benchmark-sort=fullname
========================================= test session starts ==========================================
platform darwin -- Python 3.11.2, pytest-7.4.0, pluggy-1.2.0
benchmark: 4.0.0 (defaults: timer=time.perf_counter disable_gc=True min_rounds=5 min_time=0.000005 max_time=1.0 calibration_precision=10 warmup=False warmup_iterations=5)
rootdir: /code/kuzudb-study/kuzudb
plugins: Faker-19.2.0, anyio-3.7.1, benchmark-4.0.0
collected 10 items                                                                                     

benchmark_query.py ..........                                                                    [100%]


-------------------------------------------------------------------------------------- benchmark: 10 tests --------------------------------------------------------------------------------------
Name (time in ms)               Min                 Max                Mean             StdDev              Median                IQR            Outliers       OPS            Rounds  Iterations
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_benchmark_query1      187.6215 (42.79)    215.1583 (40.93)    201.2965 (41.81)    10.8608 (34.30)    200.3082 (41.39)    17.0231 (62.64)         2;0    4.9678 (0.02)          5           1
test_benchmark_query10     769.6619 (175.53)   801.6863 (152.51)   781.0308 (162.21)   13.8731 (43.81)    773.9472 (159.92)   21.4789 (79.04)         1;0    1.2804 (0.01)          5           1
test_benchmark_query2      224.0829 (51.10)    263.8683 (50.20)    249.3954 (51.79)    16.1696 (51.07)    256.7539 (53.05)    22.2899 (82.02)         1;0    4.0097 (0.02)          5           1
test_benchmark_query3       10.1482 (2.31)      12.0562 (2.29)      10.9885 (2.28)      0.3852 (1.22)      11.0705 (2.29)      0.2835 (1.04)         11;9   91.0040 (0.44)         44           1
test_benchmark_query4        8.7894 (2.00)      19.4709 (3.70)      10.3636 (2.15)      1.8377 (5.80)       9.7671 (2.02)      1.1838 (4.36)          5;5   96.4919 (0.46)         69           1
test_benchmark_query5        4.3848 (1.0)        5.2565 (1.0)        4.8151 (1.0)       0.3166 (1.0)        4.8396 (1.0)       0.6334 (2.33)         15;0  207.6812 (1.0)          32           1
test_benchmark_query6       28.5645 (6.51)      31.3298 (5.96)      29.8180 (6.19)      0.6957 (2.20)      29.9759 (6.19)      1.1007 (4.05)         11;0   33.5368 (0.16)         32           1
test_benchmark_query7        7.0635 (1.61)       8.9225 (1.70)       7.8995 (1.64)      0.3691 (1.17)       7.8556 (1.62)      0.2718 (1.0)         18;15  126.5904 (0.61)         71           1
test_benchmark_query8       99.0060 (22.58)    123.4725 (23.49)    108.2653 (22.48)     7.8141 (24.68)    107.2657 (22.16)    12.5305 (46.11)         3;0    9.2366 (0.04)         10           1
test_benchmark_query9      854.6426 (194.91)   932.6182 (177.42)   889.0417 (184.64)   33.3944 (105.46)   874.2172 (180.64)   55.3503 (203.68)        2;0    1.1248 (0.01)          5           1
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Legend:
  Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
  OPS: Operations Per Second, computed as 1 / Mean
========================================= 10 passed in 20.84s ==========================================
```

#### Query performance (Kùzu multi-threaded)

```sh
$ pytest benchmark_query.py --benchmark-min-rounds=5 --benchmark-warmup-iterations=5 --benchmark-disable-gc --benchmark-sort=fullname
========================================= test session starts ==========================================
platform darwin -- Python 3.11.2, pytest-7.4.0, pluggy-1.2.0
benchmark: 4.0.0 (defaults: timer=time.perf_counter disable_gc=True min_rounds=5 min_time=0.000005 max_time=1.0 calibration_precision=10 warmup=False warmup_iterations=5)
rootdir: /code/kuzudb-study/kuzudb
plugins: Faker-19.2.0, anyio-3.7.1, benchmark-4.0.0
collected 10 items                                                                                     

benchmark_query.py ..........                                                                    [100%]


-------------------------------------------------------------------------------------- benchmark: 10 tests --------------------------------------------------------------------------------------
Name (time in ms)               Min                 Max                Mean             StdDev              Median                IQR            Outliers       OPS            Rounds  Iterations
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_benchmark_query1      113.0014 (28.40)    245.0873 (44.68)    145.0578 (30.04)    56.2668 (185.80)   123.1903 (25.58)    43.0426 (136.11)        1;1    6.8938 (0.03)          5           1
test_benchmark_query10     540.2672 (135.81)   627.5628 (114.40)   563.2572 (116.63)   36.4845 (120.48)   550.6263 (114.33)   31.8747 (100.80)        1;1    1.7754 (0.01)          5           1
test_benchmark_query2      123.9972 (31.17)    132.6335 (24.18)    128.1020 (26.53)     2.8402 (9.38)     127.9745 (26.57)     3.6837 (11.65)         2;0    7.8063 (0.04)          7           1
test_benchmark_query3        7.3900 (1.86)       9.4403 (1.72)       8.1829 (1.69)      0.4120 (1.36)       8.0602 (1.67)      0.4682 (1.48)         19;1  122.2061 (0.59)         63           1
test_benchmark_query4        7.1140 (1.79)       9.1029 (1.66)       7.9130 (1.64)      0.3950 (1.30)       7.7692 (1.61)      0.6243 (1.97)         24;0  126.3748 (0.61)         82           1
test_benchmark_query5        3.9783 (1.0)        5.4857 (1.0)        4.8294 (1.0)       0.3028 (1.0)        4.8161 (1.0)       0.3434 (1.09)         16;2  207.0671 (1.0)          64           1
test_benchmark_query6       11.2117 (2.82)      13.8597 (2.53)      12.5634 (2.60)      0.5755 (1.90)      12.4724 (2.59)      0.8934 (2.83)         19;0   79.5963 (0.38)         66           1
test_benchmark_query7        5.8453 (1.47)       7.3942 (1.35)       6.5953 (1.37)      0.3223 (1.06)       6.5524 (1.36)      0.3162 (1.0)          27;6  151.6239 (0.73)         84           1
test_benchmark_query8       22.7547 (5.72)      30.6260 (5.58)      25.0031 (5.18)      1.7501 (5.78)      24.6404 (5.12)      2.7679 (8.75)         11;1   39.9951 (0.19)         38           1
test_benchmark_query9      586.4883 (147.42)   605.2226 (110.33)   591.1415 (122.41)    7.9578 (26.28)    587.3650 (121.96)    6.5644 (20.76)         1;1    1.6916 (0.01)          5           1
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Legend:
  Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
  OPS: Operations Per Second, computed as 1 / Mean
========================================= 10 passed in 15.53s ==========================================
```

