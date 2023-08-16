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
Nodes loaded in 0.0872s
Edges loaded in 2.0920s
```

> 💡 Ingesting the nodes/edges via the CSV bulk loader in KùzuDB takes under 3 seconds 🔥, as opposed to ~65 seconds for Neo4j. The timing shown is on an M2 Macbook Pro with 16 GB of RAM.

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

#### Output

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
Query 1 completed in 0.338447s

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
Query 2 completed in 0.754088s

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
│ Montreal  ┆ 37.310934  │
│ Calgary   ┆ 37.592098  │
│ Toronto   ┆ 37.705746  │
│ Edmonton  ┆ 37.931609  │
│ Vancouver ┆ 38.011002  │
└───────────┴────────────┘
Query 3 completed in 0.012301s

Query 4:
 
        MATCH (p:Person)-[:LivesIn]->(ci:City)-[*1..2]->(country:Country)
        WHERE p.age > $age_lower AND p.age < $age_upper
        RETURN country.country AS countries, count(country) AS personCounts
        ORDER BY personCounts DESC LIMIT 3;
    
Persons between ages 30-40 in each country:
shape: (3, 2)
┌────────────────┬──────────────┐
│ countries      ┆ personCounts │
│ ---            ┆ ---          │
│ str            ┆ i64          │
╞════════════════╪══════════════╡
│ United States  ┆ 24983        │
│ Canada         ┆ 2514         │
│ United Kingdom ┆ 1498         │
└────────────────┴──────────────┘
Query 4 completed in 0.017814s

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
Query 5 completed in 0.012881s

Query 6:
 
        MATCH (p:Person)-[:HasInterest]->(i:Interest)
        WHERE lower(i.interest) = lower($interest)
        AND p.gender = $gender
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
Query 6 completed in 0.035519s

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
│ 169        ┆ California ┆ United States │
└────────────┴────────────┴───────────────┘
            
Query 7 completed in 0.014666s

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
Query 8 completed in 0.103491s
Queries completed in 1.2895s
```

### Query performance

The numbers shown below are for when we ingest 100K person nodes, ~10K location nodes and ~2.4M edges into the graph. Query times for simple aggregation and path finding are relatively low. More advanced queries involving variable length paths will be studied later.

Summary of run times:

* Query 1: `0.338447s`
* Query 2: `0.754088s`
* Query 3: `0.012301s`
* Query 4: `0.017814s`
* Query 5: `0.012881s`
* Query 6: `0.035519s`
* Query 7: `0.014666s`
* Query 8: `0.103491s`

> 💡 All queries (including materializing the results to arrow tables and then polars) take just over 1 sec 🔥 to complete (Neo4j takes over 4x longer). The timing shown is for queries run in a single execution thread on an M2 Macbook Pro with 16 GB of RAM.
