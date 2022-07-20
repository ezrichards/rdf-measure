# Measurement apparatus for RDF encodings
import os
import time
import rdflib
import json
from dataclasses import dataclass, field
import pandas as pd
from typing import List

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
  
    def encoding_time(self) -> List[float]:
        """
        Return N_RUNS samples of how long it takes
        to encode the file
        """
        samples = []

        for _ in range(0, self.N_RUNS):
            graph = rdflib.Graph()
            graph.parse(self.graph_file)
            start = time.time()

            # using ID-graph dictionary compression
            idTerm = {}
            triples = []

            for s, p, o in graph:
                idTerm.update({hash(s): s})
                idTerm.update({hash(p): p})
                idTerm.update({hash(o): o})

                triple = [] 

                triple.append(hash(s))
                triple.append(hash(p))
                triple.append(hash(o))

                triples.append(triple)

            idTerm.update({"triples": triples})

            end = time.time()
            samples.append(end - start)
                
            with open('data.json', 'w', encoding='utf-8') as file:
                json.dump(idTerm, file, ensure_ascii=False, indent=4)

        return samples

    # TODO for decode, read JSON file and then delete when done
    def decoding_time(self) -> List[float]:
        """
        Return N_RUNS samples of how long it takes
        to decode the file
        """
        samples = []

        for i in range(0, self.N_RUNS):
            graph = rdflib.Graph()
            
            start = time.time()
            graph.parse(self.graph_file)
            end = time.time()

            samples.append(end - start)

        return samples

class NTriples(Format):
    # etc
    pass

class Turtle(Format):
    # etc
    pass

class JSONLD(Format):
    # etc
    pass

class RDFXML(Format):
    # etc
    pass

results: List[pd.DataFrame] = [
    NTriples(graph_file='graphs/bldg1.ttl', name='NTriples').run()
]

# 1 dataframe with all benchmarks
all_results = pd.concat(results, axis=1)

# export to csv so it can be used in a notebook
# all_results.to_csv('results.csv', sep=',', index=False)