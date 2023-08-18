# Data generation for study

This section describes the individual data generation scripts to build the nodes and edges of the artificial social network.

## Generate all data at once

As mentioned in the root level README, a shell script `generate_data.sh` is provided that sequentially runs the Python scripts from this directory, generating the data for the nodes and edges for the social network. This is the recommended way to generate the data. A single positional argument is provided to the shell script: The number of person profiles to generate, specified as an integer value as shown below.

```sh
# Generate data for 100K persons
bash generate_data.sh 100000
```

Running this command generates a series of files in the `output` directory, following which we can proceed to ingesting the data into a graph database.

### Nodes: Persons

First, fake male and female profile information is generated for the number of people required to be in the network.

```sh
$ cd data
# Create a dataset of fake profiles for men and women with a 50-50 split by gender
$ python create_nodes_person.py -n 100000
```

The parquet file generated fake person metadata, and looks like the below.


id|name|gender|birthday|age|isMarried
---|---|---|---|---|---
1|Kenneth Scott|male|1984-04-14|39|true
2|Stephanie Lozano|female|1993-12-31|29|true
3|Thomas Williams|male|1979-02-09|44|true

Because the parquet format encodes the data types as inferred from the underlying arrow schema, we can be assured that the data, for example, `age`, is correctly stored of the type `date`. This reduces the verbosity of the code when compared to the CSV format, which would required us to clearly specify the separator and then re-parse the data to the correct type when using it downstream.

### Nodes: Locations

To generate a list of cities that people live in, we use the [world cities dataset](https://www.kaggle.com/datasets/juanmah/world-cities?resource=download) from Kaggle. This is an accurate and up-to-date database of the world's cities and towns, including lat/long and population information of ~44k cities all over the world.

To make this dataset simpler and more realistic, we only consider cities from the following three countries: `US`, `UK` and `CA`.

```sh
$ python create_nodes_location.py

Wrote 7117 cities to parquet
Wrote 273 states to parquet
Wrote 3 countries to parquet
```

Three parquet files are generated accordingly for cities, states and the specified countries. Latitude, longitude and population are the additional metadata fields for each city, each stored with the appropriate data type within the file's schema.

#### `cities.parquet`

id|city|state|country|lat|lng|population
---|---|---|---|---|---|---
1|Airdrie|Alberta|Canada|51.2917|-114.0144|61581
2|Beaumont|Alberta|Canada|53.3572|-113.4147|17396

#### `states.parquet`

id|state|country
---|---|---
1|Alberta|Canada
2|British Columbia|Canada
3|Manitoba|Canada

#### `countries.parquet`

id|country
---|---
1|Canada
2|United Kingdom
3|United States

### Nodes: Interests

A static list of interests/hobbies that a person could have is included in `raw/interests.parquet`. This is cleaned up and formatted as required by the data generator script.

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

Edges are generated between cities and the states they are in, as per the `cities.parquet` file

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

Edges are generated between states and the countries they are in, as per the `states.parquet` file

```sh
python create_edges_state_country.py
```

The data generated contains the state ID in the `from` column and the country ID in the `to` column.

from|to
---|---
1|1
2|1
3|1

## Dataset files

The following files are generated by the scripts in this directory.

### Nodes

In the `./output/nodes` directory, the following files are generated.

* `persons.parquet`
* `interests.parquet`
* `cities.parquet`
* `states.parquet`
* `countries.parquet`


### Edges

In the `./output/edges` directory, the following files are generated.

* `follows.parquet`
* `lives_in.parquet`
* `interests.parquet`
* `city_in.parquet`
* `state_in.parquet`
