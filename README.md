# KùzuDB: Benchmark study

Code for the benchmark study described in this [blog post](https://thedataquarry.com/posts/embedded-db-2/).

Neo4j version | Kùzu version | Python version
:---: | :---: | :---:
5.26.0 (community) | 0.7.0 | 3.12.5

[Kùzu](https://kuzudb.com/) is an in-process (embedded) graph database management system (GDBMS) written in C++. It is blazing fast 🔥, and is optimized for handling complex join-heavy analytical workloads on very large graphs. Kùzu's [goal](https://kuzudb.com/docusaurus/blog/what-every-gdbms-should-do-and-vision) is to do in the graph database world what DuckDB has done in the world of relational databases -- that is, to provide a fast, lightweight, embeddable graph database for analytics (OLAP) use cases, while being heavily focused on usability and developer productivity.

This study has the following goals:

* Generate an artificial social network dataset, including persons, interests and locations
  * You can scale up the size of the artificial dataset using the scripts provided and test query performance on larger graphs
* Ingest the dataset into two graph databases: Kùzu and Neo4j (community edition)
* Run a set of queries in Cypher on either DB to:
  * (1) Verify that the data is ingested correctly and that the results from either DB are consistent with one another
  * (2) Compare the query performance on a suite of queries that involve multi-hop traversals and aggregations

Python (and the associated client APIs for either DB) are used to orchestrate the pipelines throughout.

## Setup

Activate a Python virtual environment and install the dependencies as follows.

```sh
# Assuming that the uv package manager is installed
# https://github.com/astral-sh/uv
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
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

## Graph schema

The following graph schema is used for the social network dataset.

![](./assets/kuzudb-graph-schema.png)

* `Person` node `FOLLOWS` another `Person` node
* `Person` node `LIVES_IN` a `City` node
* `Person` node `HAS_INTEREST` towards an `Interest` node
* `City` node is `CITY_IN` a `State` node
* `State` node is `STATE_IN` a `Country` node

## Ingest the data into Neo4j or Kùzu

Navigate to the [neo4j](./neo4j) and the [kuzudb](./kuzudb/) directories to see the instructions on how to ingest the data into each database.

The generated graph is a well-connected graph, and a sample of `Person`-`Person` connections as visualized in the Neo4j browser is shown below. Certain groups of persons form a clique, and some others are central hubs with many connections, and each person can have many interests, but only one primary residence city.

![](./assets/person-person.png)

## Run the queries

Some sample queries are run in each DB to verify that the data is ingested correctly, and that the results are consistent with one another.

The following questions are asked of both graphs:

* **Query 1**: Who are the top 3 most-followed persons?
* **Query 2**: In which city does the most-followed person live?
* **Query 3**: Which 5 cities in a particular country have the lowest average age in the network?
* **Query 4**: How many persons between ages 30-40 are there in each country?
* **Query 5**: How many men in London, United Kingdom have an interest in fine dining?
* **Query 6**: Which city has the maximum number of women that like Tennis?
* **Query 7**: Which U.S. state has the maximum number of persons between the age 23-30 who enjoy photography?
* **Query 8**: How many second-degree paths exist in the graph?
* **Query 9**: How many paths exist in the graph through persons age 50 to persons above age 25?


## Performance comparison

The run times for both ingestion and queries are compared.

* For ingestion, KùzuDB is consistently faster than Neo4j by a factor of **~18x** for a 
* For OLAP queries, KùzuDB is **significantly faster** than Neo4j, especially for ones that involve multi-hop queries via nodes with many-to-many relationships.

### Benchmark conditions

- Machine: M3 Macbook Pro with 36 GB RAM.
- Graph size: 100K nodes, ~2.4M edges.

### Ingestion performance

Case | Neo4j (sec) | Kùzu (sec) | Speedup factor
--- | ---: | ---: | ---:
Nodes | 1.85 | 0.13 | 14.2x
Edges | 28.79 | 0.45 | 64.0x
Total | 30.64 | 0.58 | 52.8x

Nodes are ingested significantly faster in Kùzu, and using its community edition, Neo4j's node ingestion
remains of the order of seconds
despite setting constraints on the ID fields as per their best practices. The speedup factors shown
are expected to be even higher as the dataset gets larger and larger using this approach, and
the only way to speed up Neo4j data ingestion is to use `admin-import` instead (however, this means
you lose the ability to work in Python and have to switch languages).

### Query performance benchmark

The full benchmark numbers are in the `README.md` pages for respective directories for `neo4j` and `kuzudb`, with the high-level summary shown below.

#### Notes on benchmark timing

The benchmarks are run via the `pytest-benchmark` library for the query scripts for either DB. `pytest-benchmark`, which is built on top of `pytest`, attaches each set of runs to a timer. It uses the Python time module's [`time.perf_counter`](https://docs.python.org/3/library/time.html#time.perf_counter), which has a resolution of 500 ns, smaller than the run time of the fastest query in this dataset.

* 5 warmup runs are performed to ensure byte code compilation and to warm up the cache prior to measuring run times
* Each query is run for a **minimum of 5 rounds**, so the run times shown in each section below as the **average over a minimum of 5 rounds**, or upwards of 50 rounds.
  * Long-running queries (where the total run time exceeds 1 sec) are run for at least 5 rounds.
  * Short-running queries (of the order of milliseconds) will run as many times as fits into a period of 1 second, so the fastest queries can run upwards of 50 times.
* Python's own GC overhead can obscure true run times, so the `benchmark-disable-gc` argument is enabled.

See the [`pytest-benchmark` docs](https://pytest-benchmark.readthedocs.io/en/latest/calibration.html) to see how they calibrate their timer and group the rounds.

#### Neo4j vs. Kùzu

KùzuDB supports multi-threaded execution of queries with maximum thread utilization as available on the machine.
The run times for each query (averaged over the number of rounds run, guaranteed to be a minimum of 5 runs) are shown below.

Query | Neo4j (sec) | Kùzu (sec) | Speedup factor
--- | ---: | ---: | ---:
1 | 1.7267 | 0.1603 | 10.77
2 | 0.6073 | 0.2498 | 2.43
3 | 0.0376 | 0.0085 | 4.42
4 | 0.0411 | 0.0147 | 2.80
5 | 0.0075 | 0.0134 | 0.56
6 | 0.0194 | 0.0362 | 0.54
7 | 0.1384 | 0.0151 | 9.17
8 | 3.2203 | 0.0086 | 374.45
9 | 3.8970 | 0.0955 | 40.81

> 🔥 The n-hop path-finding queries (8 and 9) show the biggest speedup over Neo4j, due to core innovations in Kùzu's query engine.

### Ideas for future work

#### Scale up the dataset

You can attempt to generate a much larger artificial dataset of ~100M nodes and ~2.5B edges, and see how the performance of Kùzu and Neo4j compare, if you're interested.

```sh
# Generate data with 100M persons and ~2.5B edges (takes a long time in Python!)
bash generate_data.sh 100000000
```

The above script can take really long to run in Python. [Here's an example](https://github.com/thedataquarry/rustinpieces/tree/main/src/mock_data)
of using the `fake-rs` crate in Rust to do this much faster.

#### Relationship property aggregation

The queries 1-9 in this benchmark are all on node properties. You can add relationship properties in the dataset
to see how the two DBs compare when aggregating on them. For example, add a `since` date property on the
`Follows` edges to run filter queries on how long a person has been following another person.
