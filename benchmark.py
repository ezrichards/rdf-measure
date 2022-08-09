# Measurement apparatus for RDF encodings
import os
import time
import rdflib
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from dataclasses import dataclass, field
from typing import List
from farmhash import FarmHash32

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
            triples = []
            idTerms = {}

            for s, p, o in graph:
                idTerms.update({str(FarmHash32(s)): s})
                idTerms.update({str(FarmHash32(p)): p})
                idTerms.update({str(FarmHash32(o)): o})
                triples.append((FarmHash32(s), FarmHash32(p), FarmHash32(o)))

            end = time.time()
            samples.append(end - start)

            termDataframe = pd.DataFrame({
                "terms": idTerms
            })

            tripleDataframe = pd.DataFrame({
                "triples": triples
            })

            # to HTML just for debugging
            # termDataframe.to_html("terms.html")
            # tripleDataframe.to_html("triples.html")

            termsTable = pa.Table.from_pandas(termDataframe, preserve_index=True)
            triplesTable = pa.Table.from_pandas(tripleDataframe)

            pq.write_table(termsTable, "terms.parquet")
            pq.write_table(triplesTable, "triples.parquet")

        return samples

    def decoding_time(self, serialization_format) -> List[float]:
        """
        Return N_RUNS samples of how long it takes
        to decode the file
        """
        samples = []

        for i in range(0, self.N_RUNS):
            start = time.time()
            graph = rdflib.Graph()

            termsTable = pq.read_table('terms.parquet').to_pandas()
            triplesTable = pq.read_table('triples.parquet')

            terms = termsTable.to_dict()
            for triple in triplesTable.to_pydict()['triples']:
                s = rdflib.URIRef(terms['terms'][str(triple[0])])
                p = rdflib.URIRef(terms['terms'][str(triple[1])])
                o = rdflib.Literal(terms['terms'][str(triple[2])])
                graph.add((s, p, o))

            graph.serialize(format=serialization_format)
            end = time.time()
            samples.append(end - start)

        return samples

class NTriples(Format):
    def encoding_time(self) -> List[float]:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)
        graph.serialize(format='n3')
        return super().encoding_time(graph)

    def decoding_time(self) -> List[float]:
        return super().decoding_time("n3")

class Turtle(Format):
    def encoding_time(self) -> List[float]:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)
        graph.serialize(format='ttl')
        return super().encoding_time(graph)

    def decoding_time(self) -> List[float]:
        return super().decoding_time("ttl")

class JSONLD(Format):
    def encoding_time(self) -> List[float]:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)
        graph.serialize(format='json-ld')
        return super().encoding_time(graph)

    def decoding_time(self) -> List[float]:
        return super().decoding_time("json-ld")

class RDFXML(Format):
    def encoding_time(self) -> List[float]:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)
        graph.serialize(format='xml')
        return super().encoding_time(graph)

    def decoding_time(self) -> List[float]:
        return super().decoding_time("xml")

results: List[pd.DataFrame] = [
    NTriples(graph_file='graphs/bldg1.ttl', name='NTriples').run(),
    Turtle(graph_file='graphs/bldg1.ttl', name='Turtle').run(),
    JSONLD(graph_file='graphs/bldg1.ttl', name='JSON-LD').run(),
    RDFXML(graph_file='graphs/bldg1.ttl', name='RDF-XML').run()
]

# 1 dataframe with all benchmarks
all_results = pd.concat(results, axis=1)

# export to csv so it can be used in a notebook
all_results.to_csv('results.csv', sep=',', index=False)
