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
│ 45632026 │
└──────────┘
        
Queries completed in 1.0300s
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
collected 9 items                                                                                

benchmark_query.py .........                                                               [100%]


-------------------------------------------------------------------------------------- benchmark: 9 tests --------------------------------------------------------------------------------------
Name (time in ms)              Min                 Max                Mean             StdDev              Median                IQR            Outliers       OPS            Rounds  Iterations
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_benchmark_query1     189.0859 (43.92)    232.4099 (44.28)    203.3761 (44.12)    18.0788 (67.79)    195.9212 (43.49)    24.9847 (151.61)        1;0    4.9170 (0.02)          5           1
test_benchmark_query2     222.0232 (51.57)    247.1910 (47.10)    234.2920 (50.83)    10.2823 (38.56)    232.4413 (51.60)    16.9951 (103.13)        2;0    4.2682 (0.02)          5           1
test_benchmark_query3      10.2753 (2.39)      11.9916 (2.28)      10.8182 (2.35)      0.4837 (1.81)      10.5846 (2.35)      0.6887 (4.18)          7;0   92.4367 (0.43)         44           1
test_benchmark_query4       8.5602 (1.99)       9.9832 (1.90)       8.9210 (1.94)      0.2979 (1.12)       8.7935 (1.95)      0.2700 (1.64)         11;6  112.0955 (0.52)         68           1
test_benchmark_query5       4.3054 (1.0)        5.2484 (1.0)        4.6097 (1.0)       0.2667 (1.0)        4.5051 (1.0)       0.1648 (1.0)           9;7  216.9336 (1.0)          34           1
test_benchmark_query6      28.3205 (6.58)      34.3160 (6.54)      29.5330 (6.41)      1.2513 (4.69)      29.0962 (6.46)      1.4753 (8.95)          3;1   33.8605 (0.16)         33           1
test_benchmark_query7       7.0241 (1.63)       8.2802 (1.58)       7.6011 (1.65)      0.2749 (1.03)       7.6395 (1.70)      0.3191 (1.94)         21;1  131.5593 (0.61)         71           1
test_benchmark_query8      82.9250 (19.26)     88.3274 (16.83)     85.3055 (18.51)     1.4860 (5.57)      85.0121 (18.87)     1.9935 (12.10)         2;0   11.7226 (0.05)         10           1
test_benchmark_query9      92.0145 (21.37)    101.1665 (19.28)     95.1086 (20.63)     2.6232 (9.84)      94.3967 (20.95)     3.7115 (22.52)         2;0   10.5143 (0.05)         11           1
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Legend:
  Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
  OPS: Operations Per Second, computed as 1 / Mean
======================================= 9 passed in 9.80s ========================================
```

#### Query performance (Kùzu multi-threaded)

```sh
$ pytest benchmark_query.py --benchmark-min-rounds=5 --benchmark-warmup-iterations=5 --benchmark-disable-gc --benchmark-sort=fullname

====================================== test session starts =======================================
platform darwin -- Python 3.11.2, pytest-7.4.0, pluggy-1.2.0
benchmark: 4.0.0 (defaults: timer=time.perf_counter disable_gc=True min_rounds=5 min_time=0.000005 max_time=1.0 calibration_precision=10 warmup=False warmup_iterations=5)
rootdir: /code/kuzudb-study/kuzudb
plugins: Faker-19.2.0, anyio-3.7.1, benchmark-4.0.0
collected 9 items                                                                                

benchmark_query.py .........                                                               [100%]


-------------------------------------------------------------------------------------- benchmark: 9 tests -------------------------------------------------------------------------------------
Name (time in ms)              Min                 Max                Mean             StdDev              Median               IQR            Outliers       OPS            Rounds  Iterations
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_benchmark_query1     111.8345 (28.83)    142.8120 (24.57)    119.3300 (25.60)    13.1853 (37.02)    114.0637 (24.84)    9.4650 (34.61)         1;1    8.3801 (0.04)          5           1
test_benchmark_query2     122.8597 (31.67)    133.4399 (22.96)    125.9888 (27.03)     3.4414 (9.66)     124.9305 (27.20)    3.1156 (11.39)         1;1    7.9372 (0.04)          8           1
test_benchmark_query3       7.6189 (1.96)       8.9303 (1.54)       8.1799 (1.75)      0.3647 (1.02)       8.0242 (1.75)     0.6900 (2.52)         20;0  122.2512 (0.57)         49           1
test_benchmark_query4       6.6943 (1.73)       9.3038 (1.60)       7.8041 (1.67)      0.4324 (1.21)       7.8203 (1.70)     0.3738 (1.37)         16;9  128.1380 (0.60)         71           1
test_benchmark_query5       3.8793 (1.0)        5.8129 (1.0)        4.6616 (1.0)       0.3562 (1.0)        4.5923 (1.0)      0.2734 (1.0)          10;6  214.5167 (1.0)          43           1
test_benchmark_query6      11.2139 (2.89)      16.2617 (2.80)      12.7203 (2.73)      0.8346 (2.34)      12.5488 (2.73)     0.9154 (3.35)         16;3   78.6143 (0.37)         79           1
test_benchmark_query7       5.9201 (1.53)       8.8597 (1.52)       6.7574 (1.45)      0.4744 (1.33)       6.6542 (1.45)     0.5415 (1.98)         16;4  147.9860 (0.69)         91           1
test_benchmark_query8      17.9653 (4.63)      24.0970 (4.15)      19.1212 (4.10)      1.5263 (4.28)      18.5978 (4.05)     0.2817 (1.03)          1;5   52.2979 (0.24)         15           1
test_benchmark_query9      21.0242 (5.42)      24.2167 (4.17)      22.6162 (4.85)      0.7493 (2.10)      22.6565 (4.93)     1.1582 (4.24)         15;0   44.2161 (0.21)         42           1
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Legend:
  Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
  OPS: Operations Per Second, computed as 1 / Mean
======================================= 9 passed in 7.91s ========================================
```

