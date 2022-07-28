# Measurement apparatus for RDF encodings
import os
import time
import rdflib
from rdflib.util import from_n3
import json
from dataclasses import dataclass, field
import pandas as pd
from typing import List
from farmhash import FarmHash32
import pyarrow as pa
import pyarrow.parquet as pq

@dataclass
class Format:
    # the graph to be benchmarked
    graph_file: str
    # name of the format
    name: str
    # benchmarks
    records: list = field(default_factory=list)

    # how many runs to do
    N_RUNS = 100

    def run(self):
        """
        Runs all of the benchmarks
        """
        self.add_records(self.size)
        self.add_records(self.encoding_time)
        self.add_records(self.decoding_time)

        df = pd.DataFrame.from_records(self.records)
        self.records = []
        return df

    def add_records(self, bench_fn):
        benchmark_results = bench_fn()
        benchmark_name = bench_fn.__name__
        if not isinstance(benchmark_results, list):
            benchmark_results = [benchmark_results]
        for res in benchmark_results:
            self.records.append({
                'name': self.name,
                'benchmark': benchmark_name,
                'value': res,
                'graph': self.graph_file,
            })

    def size(self) -> int:
        """
        Return the size of the format, in bytes
        """
        return os.path.getsize(self.graph_file)

    def encoding_time(self, graph) -> List[float]:
        """
        Return N_RUNS samples of how long it takes
        to encode the file
        """        
        samples = []
        for _ in range(0, self.N_RUNS):
            start = time.time()

            # using ID-graph dictionary compression
            idTerm = {}
            idTerms = {}
            triples = []

            for s, p, o in graph:
                idTerms.update({str(FarmHash32(s)): s})
                idTerms.update({str(FarmHash32(p)): p})
                idTerms.update({str(FarmHash32(o)): o})

                triple = [] 

                triple.append(FarmHash32(s))
                triple.append(FarmHash32(p))
                triple.append(FarmHash32(o))

                triples.append(triple)

            idTerm.update({"idTerm": idTerms})
            idTerm.update({"triples": triples})

            end = time.time()
            samples.append(end - start)

            with open('data.json', 'w', encoding='utf-8') as file:
                json.dump(idTerm, file, ensure_ascii=False, indent=4)
            
            df = pd.DataFrame.from_dict(idTerms, orient='index')
            
            table = pa.Table.from_pandas(df)

            print(table)

            pq.write_table(table, "data1.parquet")

        return samples

    def decoding_time(self) -> List[float]:
        """
        Return N_RUNS samples of how long it takes
        to decode the file
        """
        samples = []

        for i in range(0, self.N_RUNS):
            start = time.time()
            graph = rdflib.Graph()

            file = open('data.json')
            data = json.load(file)

            table = pq.read_table('data1.parquet')

            # print("DECODE:", table.to_pandas())

            for triple in data['triples']:
                s = rdflib.URIRef(data['idTerm'][str(triple[0])])
                p = rdflib.URIRef(data['idTerm'][str(triple[1])])
                o = rdflib.Literal(data['idTerm'][str(triple[2])])
                graph.add((s, p, o))

            file.close()
            end = time.time()
            samples.append(end - start)

        return samples

class NTriples(Format):
    def encoding_time(self) -> List[float]:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)
        graph.serialize(format='n3')
        super().encoding_time(graph)

class Turtle(Format):
    def encoding_time(self) -> List[float]:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)
        graph.serialize(format='ttl')
        super().encoding_time(graph)

class JSONLD(Format):
    def encoding_time(self) -> List[float]:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)
        graph.serialize(format='json-ld')
        super().encoding_time(graph)

class RDFXML(Format):
    def encoding_time(self) -> List[float]:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)
        graph.serialize(format='xml')
        super().encoding_time(graph)

results: List[pd.DataFrame] = [
    NTriples(graph_file='graphs/bldg1.ttl', name='NTriples').run(),
    # Turtle(graph_file='graphs/bldg1.ttl', name='Turtle').run(),
    # JSONLD(graph_file='graphs/bldg1.ttl', name='JSON-LD').run(),
    # RDFXML(graph_file='graphs/bldg1.ttl', name='RDF-XML').run()
]

# 1 dataframe with all benchmarks
all_results = pd.concat(results, axis=1)

# export to csv so it can be used in a notebook
# all_results.to_csv('results.csv', sep=',', index=False)
