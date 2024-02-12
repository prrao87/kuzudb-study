#!/bin/bash

source .venv/bin/activate
cd data

# Specify number of person profiles (integer) as an argument
# Default value is 1000
echo "Generating $1 samples of data";

# Nodes
python create_nodes_person.py -n ${1-1000}
python create_nodes_location.py
python create_nodes_interests.py

# Edges
python create_edges_follows.py
python create_edges_location.py
python create_edges_interests.py
python create_edges_location_city_state.py
python create_edges_location_state_country.py
