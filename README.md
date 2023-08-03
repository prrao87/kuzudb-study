# KùzuDB: Benchmark study

[Kùzu](https://kuzudb.com/) is an in-process (embedded) graph database management system (GDBMS) built for query speed and scalability. It is written in C++, optimized for handling complex join-heavy analytical workloads on very large graph databases, and is under active development. The goal of the code shown in this repo is as follows:

* Generate an artificial dataset that can be used to build
* Ingest the data into Kùzu
* Run a set of queries in Cypher on the data to benchmark the performance of Kùzu
* Study the ingestion and query times in comparison with Neo4j, and optimize where possible

Python is used as the intermediary language to pass data between the source and the DB.

## Setup

Activate a Python virtual environment and install the dependencies as follows.

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Data

An artificial social network dataset is used, generated via the [Faker](https://faker.readthedocs.io/en/master/) Python library.

### Persons

First, fake male and female profile information is generated for the number of people required to be in the network.

```sh
cd data
# Create a dataset of 10,000 fake men and women with a 50-50 split by gender
python create_persons.py -n 10000
```

### Locations

To generate a list of cities that people live in, we use the [world cities dataset](https://www.kaggle.com/datasets/juanmah/world-cities?resource=download) from Kaggle. This is an accurate and up-to-date database of the world's cities and towns, including lat/long and population information of ~44k cities all over the world.

