# KùzuDB: Benchmark study

[Kùzu](https://kuzudb.com/) is an in-process (embedded) graph database management system (GDBMS). Because it is written in C++, it is blazing fast, and is optimized for handling complex join-heavy analytical workloads on very large graphs. The database is under active development, but its goal is to become the "DuckDB of graph databases" -- a fast, lightweight, embeddable graph database for analytics (OLAP) use cases, with minimal setup time.

The goal of the code shown in this repo is as follows:

* Generate an artificial social network dataset, including persons, interests and locations
  * It's quite easy to scale up the size of the artificial dataset using the scripts provided, so we can test the performance implications on larger graphs
* Ingest the data into KùzuDB and Neo4j
* Run a set of queries in Cypher on either DB to:
  * (1) Verify that the data is ingested correctly and that the results from either DB are consistent with one another
  * (2) Benchmark the performance of Kùzu vs. an established vendor like Neo4j
* Study the ingestion and query times for either DB, and optimize where possible

Python is used as the intermediary language between the source data and the DBs.

## Setup

Activate a Python virtual environment and install the dependencies as follows.

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Data

An artificial social network dataset is generated specifically for this exercise, via the [Faker](https://faker.readthedocs.io/en/master/) Python library.


### Generate all data at once

A shell script `generate_data.sh` is provided in the root directory of this repo that sequentially runs the Python scripts, generating the data for the nodes and edges for the social network. This is the recommended way to generate the data. A single positional argument is provided to the shell script: The number of person profiles to generate -- this is specified as an integer, as shown below.

```sh
# Generate data with 100K persons and ~2.4M edges
bash generate_data.sh 100000
```

Running this command generates a series of files in the `output` directory, following which we can proceed to ingesting the data into a graph database.

See [./data/README.md](./data/README.md) for more details on each script that is run sequentially to generate the data.

## Ingest the data into Neo4j or Kùzu

Navigate to the [neo4j](./neo4j) and the [kuzudb](./kuzudb/) directories to see the instructions on how to ingest the data into each database.

## Run the queries

Some sample queries are run in each DB to verify that the data is ingested correctly, and that the results are consistent with one another.

The following questions are asked of both graphs:

* **Query 1**: Who are the top 3 most-followed persons?
* **Query 2**: In which city does the most-followed person live?
* **Query 3**: What are the top 5 cities with the lowest average age of persons?
* **Query 4**: How many persons between ages 30-40 are there in each country?
* **Query 5**: How many men in London, United Kingdom have an interest in fine dining?
* **Query 6**: Which city has the maximum number of women that like Tennis?
* **Query 7**: Which U.S. state has the maximum number of persons between the age 23-30 who enjoy photography?
* **Query 8**: How many second-degree connections of persons are reachable in the graph?

## Performance comparison

The run times for both ingestion and queries are compared.

* For ingestion, KùzuDB is consistently faster than Neo4j by a factor of **~18x** for a graph size of 100K nodes and ~2.4M edges.
* For OLAP queries, KùzuDB is **significantly faster** than Neo4j for most types of queries, especially for ones that involve aggregating on many-to-many relationships.

### Testing conditions

* Macbook Pro M2, 16 GB RAM
* All Neo4j queries are single-threaded as per their default configuration
* Neo4j version: `5.10.0`
* KùzuDB version: `0.7.0`
* The run times reported are for the 5th run, because we want to allow the cache to warm up before gauging query performance

### Ingestion performance

In total, ~100K nodes and ~2.5 million edges are ingested **~18x** faster in KùzuDB than in Neo4j.

Case | Neo4j (sec) | Kùzu (sec) | Speedup factor
--- | ---: | ---: | ---:
Nodes | 3.6144 | 0.0874 | 41.4
Edges | 37.5801 | 2.1622 | 17.4
Total | 41.1945 | 2.2496 | 18.3

Nodes are ingested significantly faster in Kùzu (of the order of milliseconds), and Neo4j's node ingestion remains of the order of seconds despite setting constraints on the ID fields as per their best practices. The speedup factors shown are expected to be even higher as the dataset gets larger and larger, with Kùzu being around two orders of magnitude faster for inserting nodes.

### Query performance benchmark

The full benchmark numbers are in the `README.md` pages for respective directories for `neo4j` and `kuzudb`. The benchmarks are run via the `pytest-benchmark` library directly from each directory for the queries on either DB.

#### Neo4j vs. Kùzu single-threaded

The following table shows the average run times for each query, and the speedup factor of Kùzu over Neo4j.

Query | Neo4j (sec) | Kùzu (sec) | Speedup factor
--- | ---: | ---: | ---:
1 | 1.6641 | 0.1924749 | 8.6
2 | 0.5808 | 0.6697257 | 0.9
3 | 0.0052 | 0.0081793 | 0.6
4 | 0.0464 | 0.0940350 | 0.5
5 | 0.0064 | 0.0039781 | 1.6
6 | 0.0183 | 0.0277400 | 0.7
7 | 0.1539 | 0.0077988 | 19.7
8 | 0.7275 | 0.0934627 | 7.8

#### Neo4j vs. Kùzu multi-threaded

Unlike Neo4j, KùzuDB supports multi-threaded execution of queries. The following results are for the same queries as above, but allowing Kùzu to choose the optimal number of threads for each query.

Query | Neo4j (sec) | Kùzu (sec) | Speedup factor
--- | ---: | ---: | ---:
1 | 1.6641 | 0.1255608 | 13.3
2 | 0.5808 | 0.5778111 | 1.0
3 | 0.0052 | 0.0074214 | 0.7
4 | 0.0464 | 0.0085207 | 5.4
5 | 0.0064 | 0.0048872 | 1.3
6 | 0.0183 | 0.0124077 | 1.5
7 | 0.1539 | 0.0068174 | 22.6
8 | 0.7275 | 0.0211530 | 34.4

> 🔥 The second-degree path finding query (8) shows a **~34x** speedup over Neo4j for the 100K node, 2.4M edge graph, and the average speedup across all queries when using Kùzu is **~8.5x**.

It would be interesting to further study the cases where Kùzu's performance is on par with Neo4j. More to come soon!
