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

## Data

An artificial social network dataset is used, generated via the [Faker](https://faker.readthedocs.io/en/master/) Python library.


### Generate all data at once

A shell script `generate_data.sh` is provided in the root directory of this repo that sequentially runs the Python scripts, generating the data for the nodes and edges for the social network. This is the recommended way to generate the data. A single positional argument is provided to the shell script: The number of person profiles to generate.

```sh
bash generate_data.sh 1000
```

Running this command generates a series of files in the `output` directory, following which we can proceed to ingesting the data into a graph database.

### Nodes: Persons

First, fake male and female profile information is generated for the number of people required to be in the network.

```sh
$ cd data
# Create a dataset of 1000 fake profiles for men and women with a 50-50 split by gender
$ python create_nodes_person.py -n 1000
```

The CSV file generated contains a header and fake data as shown below.


id|name|gender|birthday|age|isMarried
---|---|---|---|---|---
1|Natasha Evans|female|1985-08-31|37|true
2|Gregory Smith|male|1985-11-30|37|false


The data in each column is separated by the `|` symbol to make it explicit what the column boundaries are (especially when the data itself contains commas).

### Nodes: Locations

To generate a list of cities that people live in, we use the [world cities dataset](https://www.kaggle.com/datasets/juanmah/world-cities?resource=download) from Kaggle. This is an accurate and up-to-date database of the world's cities and towns, including lat/long and population information of ~44k cities all over the world.

To make this dataset simpler and more realistic, we only consider cities from the following three countries: `US`, `UK` and `CA`. 

```sh
$ python create_nodes_location.py

Wrote 7117 cities to CSV
Wrote 273 states to CSV
Wrote 3 countries to CSV
```

Three CSV files are generated accordingly for cities, states and the specified countries. Latitude, longitude and population are the additional metadata fields for each city.

#### `cities.csv`

id|city|state|country|lat|lng|population
---|---|---|---|---|---|---
1|Airdrie|Alberta|Canada|51.2917|-114.0144|61581
2|Beaumont|Alberta|Canada|53.3572|-113.4147|17396

#### `states.csv`

id|state|country
---|---|---
1|Alberta|Canada
2|British Columbia|Canada
3|Manitoba|Canada

#### `countries.csv`

id|country
---|---
1|Canada
2|United Kingdom
3|United States

### Nodes: Interests

A static list of interests/hobbies that a person could have is included in `raw/interests.csv`. This is cleaned up and formatted as required by the data generator script.

```sh
$ python create_nodes_interests.py
```

This generates data as shown below.

id|interest
--- | ---
1|Anime
2|Art & Painting
3|Biking

### Edges: `Person` follows `Person`

Edges are generated between people in a similar way to the way we might imagine social networks. A `Person` follows another `Person`, with the direction of the edge signifying something meaningful. Rather than just generating a uniform distribution, to make the data more interesting, during generation, a small fraction of the profiles (~0.5%) is chosen to be highly connected. This resembles the role of "influencers" in real-world graphs, and in graph terminology, the nodes representing these persons can be called "hubs". The rest of the nodes are connected via these hubs in a random fashion.

```sh
python create_edges_follows.py
```

This generates data as shown below, where the `from` column contains the ID of a person who is following someone, and the `to` column contains the ID of the person being followed.

from|to
---|---
50|1
152|1
271|1

The "hub" nodes can be connected to anywhere from 0.5-5% of the number of persons in the graph.

### Edges: `Person` lives in `Location`

Edges are generated between people and the cities they live in. This is done by randomly choosing a city for each person from the list of cities generated earlier.

```sh
$ python create_edges_location.py
```

The data generated contains the person ID in the `from` column and the city ID in the `to` column.

from|to
---|---
1|6015
2|6296
3|6657

### Edges: `Person` has `Interest`

Edges are generated between people and the interests they have. This is done by randomly choosing anywhere from 1-5 interests for each person from the list of interests generated earlier for the nodes.

```sh
python create_edges_interests.py
```

The data generated contains the person ID in the `from` column and the interest ID in the `to` column.

from|to
---|---
1|24
2|4
2|8

A person can have multiple interests, so the `from` column can have multiple rows with the same ID.

### Edges: `City` is in `State`

Edges are generated between cities and the states they are in, as per the `cities.csv` file

```sh
python create_edges_city_state.py
```

The data generated contains the city ID in the `from` column and the state ID in the `to` column.

from|to
---|---
1|1
2|1
3|1

### Edges: `State` is in `Country`

Edges are generated between states and the countries they are in, as per the `states.csv` file

```sh
python create_edges_state_country.py
```

The data generated contains the state ID in the `from` column and the country ID in the `to` column.

from|to
---|---
1|1
2|1
3|1