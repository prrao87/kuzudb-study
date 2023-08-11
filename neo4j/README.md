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

The numbers shown below are for when we ingest 100K person nodes, ~10K location nodes and ~2.4M edges into the graph.

As expected, the nodes load much faster than the edges, since there are many more edges than nodes. In addition, the nodes in Neo4j are indexed (via uniqueness constraints), following which the edges are created based on a match on existing nodes. The run times for ingesting nodes and edges are output to the console.

```
Nodes loaded in 5.4609s
Edges loaded in 60.7000s
```

> 💡 Ingesting the nodes/edges with a batch size of 50K takes just over 1 minute in Neo4j. The timing shown is on an M2 Macbook Pro with 16 GB of RAM.


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

#### Output

```
Query 1 completed in 0.016359s

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
Query 2 completed in 0.002067s

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
Query 3 completed in 0.002484s

Query 3:
 
        MATCH (p:Person) -[:LIVES_IN]-> (c:City) -[*..2]-> (co:Country {country: $country})
        RETURN c.city AS city, avg(p.age) AS averageAge
        ORDER BY averageAge LIMIT 5
    
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
Query 4 completed in 0.001473s

Query 4:
 
        MATCH (p:Person)-[:LIVES_IN]->(ci:City)-[*..2]->(country:Country)
        WHERE p.age > $age_lower AND p.age < $age_upper
        RETURN country.country AS countries, count(country) AS personCounts
        ORDER BY personCounts DESC LIMIT 3
    
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
Query script completed in 2.822013s
```

### Query performance

The numbers shown below are for when we ingest 100K person nodes, ~10K location nodes and ~2.4M edges into the graph. Query times for simple aggregation and path finding are relatively low. More advanced queries involving variable length paths will be studied later.

Summary of run times:

* Query 1: `0.016359s`
* Query 2: `0.002067s`
* Query 3: `0.002484s`
* Query 4: `0.001473s`

> 💡 Query 1 takes the longest to run -- around 16 ms. Queries 2-4 (excluding data processing in Python after retrieval) takes of the order of 2 ms. The timing shown is for queries run on an M2 Macbook Pro with 16 GB of RAM.
