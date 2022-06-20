# Measurement apparatus for RDF encodings
import sys
import os
import csv
import datetime
import rdflib

file_name = input("Specify the file to measure: ")
try:
    file = open(file_name)
except OSError:
    print("Could not open file: " + file_name)
    sys.exit()

graph = rdflib.Graph()
graph.parse(file_name)

results_folder = "results-" + datetime.datetime.now().strftime("%m-%d-%Y")
if not os.path.exists(results_folder):
    os.makedirs(results_folder)

formats = ["ttl", "xml", "json-ld", "ntriples", "n3", "trig"]
metadata = [file_name, len(graph)] # original file and number of triples

with open(results_folder + '/results.csv', 'w') as file:
    writer = csv.writer(file, delimiter=',')
    writer.writerow(metadata)

    for graph_format in formats:
        serialized_file = results_folder + "/graph." + graph_format

        graph.serialize(format=graph_format, destination=serialized_file, encoding="utf-8")

        # save as format, size (in bytes)
        writer.writerow([graph_format, os.path.getsize(serialized_file)])

print(f"Results generated at {results_folder}")