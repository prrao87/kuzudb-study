# KùzuDB: Benchmark study

[Kùzu](https://kuzudb.com/) is an in-process (embedded) graph database management system (GDBMS) built for query speed and scalability. It is written in C++, optimized for handling complex join-heavy analytical workloads on very large graph databases, and is under active development. The goal of the code shown in this repo is as follows:

* Generate an artificial dataset that can be used to build an artificial social network graph
* Ingest the data into Kùzu
* Run a set of queries in Cypher on the data to benchmark the performance of Kùzu
* Study the ingestion and query times in comparison with Neo4j, and optimize where possible

Python is used as the intermediary between the source data and the DB.

## Setup

Activate a Python virtual environment and install the dependencies as follows.

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
