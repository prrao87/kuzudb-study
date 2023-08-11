# KùzuDB: Benchmark study

[Kùzu](https://kuzudb.com/) is an in-process (embedded) graph database management system (GDBMS). Because it is written in C++, it is blazing fast, and is optimized for handling complex join-heavy analytical workloads on very large graph databases. The database is under active development, but its philosophy is to become the "DuckDB of graph databases" -- a fast, lightweight, embeddable graph database for analytics use cases, with minimum setup and infrastructure effort.

The goal of the code shown in this repo is as follows:

* Generate an artificial social network dataset, including persons, interests and locations
* Ingest the data into KùzuDB and Neo4j
* Run a set of queries in Cypher on either DB to:
  * (1) Verify that the data is ingested correctly and that the results from either DB are consistent with one another
  * (2) Benchmark the performance of Kùzu vs an established vendor like Neo4j
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

An artificial social network dataset is used, generated via the [Faker](https://faker.readthedocs.io/en/master/) Python library.


### Generate all data at once

A shell script `generate_data.sh` is provided in the root directory of this repo that sequentially runs the Python scripts, generating the data for the nodes and edges for the social network. This is the recommended way to generate the data. A single positional argument is provided to the shell script: The number of person profiles to generate -- this is specified as an integer, as shown below.

```sh
bash generate_data.sh 10000
```

Running this command generates a series of files in the `output` directory, following which we can proceed to ingesting the data into a graph database.

See [./data/README.md](./data/README.md) for more details on each script that is run sequentially to generate the data.

## Ingest the data into Neo4j or Kùzu

Navigate to the [neo4j](./neo4j) and the [kuzudb](./kuzudb/) to see the instructions on how to ingest the data into each database.

## Run the queries

Some sample queries are run in each DB to verify that the data is ingested correctly, and that the results are consistent with one another.

## Performance comparison

🚧 WIP