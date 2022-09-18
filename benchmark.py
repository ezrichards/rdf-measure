# Measurement apparatus for RDF encodings
import os
import time
import json
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
        print(f"Running {self.name}..")
        self.add_records(self.encoding_time)
        self.add_records(self.decoding_time)
        self.add_records(self.size)

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
        return os.path.getsize(self.graph_file) + os.path.getsize('data.json')

    def encoding_time(self, graph) -> List[float]:
        """
        Return N_RUNS samples of how long it takes
        to encode the file
        """
        samples = []
        for _ in range(0, self.N_RUNS):
            start = time.time()
            idTerm = {}
            idTerms = {}
            triples = []

            for s, p, o in graph:
                idTerms.update({str(FarmHash32(s)): s})
                idTerms.update({str(FarmHash32(p)): p})
                idTerms.update({str(FarmHash32(o)): o})
                triples.append((FarmHash32(s), FarmHash32(p), FarmHash32(o)))

            idTerm.update({"idTerm": idTerms})
            idTerm.update({"triples": triples})

            end = time.time()
            samples.append(end - start)

            with open('data.json', 'w', encoding='utf-8') as file:
                json.dump(idTerm, file, ensure_ascii=False, indent=4)

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

            file = open('data.json')
            data = json.load(file)

            for triple in data['triples']:
                s = rdflib.URIRef(data['idTerm'][str(triple[0])])
                p = rdflib.URIRef(data['idTerm'][str(triple[1])])
                o = rdflib.Literal(data['idTerm'][str(triple[2])])
                graph.add((s, p, o))
                
            file.close()

            graph.serialize(format=serialization_format)
            end = time.time()
            samples.append(end - start)

        return samples

class NTriples(Format):
    def size(self) -> int:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)
        return len(graph.serialize(format='n3'))

    def encoding_time(self) -> List[float]:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)
        graph.serialize(format='n3')
        return super().encoding_time(graph)

    def decoding_time(self) -> List[float]:
        return super().decoding_time("n3")

class Turtle(Format):
    def size(self) -> int:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)
        return len(graph.serialize(format='ttl'))

    def encoding_time(self) -> List[float]:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)
        graph.serialize(format='ttl')
        return super().encoding_time(graph)

    def decoding_time(self) -> List[float]:
        return super().decoding_time("ttl")

class JSONLD(Format):
    def size(self) -> int:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)
        return len(graph.serialize(format='json-ld'))

    def encoding_time(self) -> List[float]:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)
        graph.serialize(format='json-ld')
        return super().encoding_time(graph)

    def decoding_time(self) -> List[float]:
        return super().decoding_time("json-ld")

class RDFXML(Format):
    def size(self) -> int:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)
        return len(graph.serialize(format='xml'))

    def encoding_time(self) -> List[float]:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)
        graph.serialize(format='xml')
        return super().encoding_time(graph)

    def decoding_time(self) -> List[float]:
        return super().decoding_time("xml")

class ParquetSorted(Format):
    def size(self) -> int:
        return os.path.getsize('terms_sorted.parquet') + os.path.getsize('triples_sorted.parquet') + os.path.getsize('data.json')

    def encoding_time(self) -> List[float]:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)

        samples = []
        for _ in range(0, self.N_RUNS):
            start = time.time()
            idTerms = {}
            subjects = []
            predicates = []
            objects = []

            for s, p, o in graph:
                idTerms.update({str(FarmHash32(s)): s})
                idTerms.update({str(FarmHash32(p)): p})
                idTerms.update({str(FarmHash32(o)): o})
                subjects.append(FarmHash32(s))
                predicates.append(FarmHash32(p))
                objects.append(FarmHash32(o))

            termDataframe = pd.DataFrame({
                "terms": idTerms
            })
    
            tripleDataframe = pd.DataFrame({
                "subject": subjects,
                "predicate": predicates,
                "object": objects
            })

            tripleDataframe = tripleDataframe.sort_values(by='subject', ascending=True)

            termsTable = pa.Table.from_pandas(termDataframe, preserve_index=True)
            triplesTable = pa.Table.from_pandas(tripleDataframe)

            pq.write_table(termsTable, "terms_sorted.parquet")
            pq.write_table(triplesTable, "triples_sorted.parquet")

            end = time.time()
            samples.append(end - start)

        return samples

    def decoding_time(self) -> List[float]:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)

        samples = []
        for i in range(0, self.N_RUNS):
            start = time.time()
            graph = rdflib.Graph()

            termsTable = pq.read_table('terms_sorted.parquet').to_pandas()
            triplesTable = pq.read_table('triples_sorted.parquet').to_pandas()

            terms = termsTable.to_dict()
            triples = triplesTable.to_dict()

            tripleTuples = []
            for i in range(0, len(triples['subject'])):
                tripleTuples.append((triples['subject'][i], triples['predicate'][i], triples['object'][i]))

            for s, p, o in tripleTuples:
                s = rdflib.URIRef(terms['terms'][str(s)])
                p = rdflib.URIRef(terms['terms'][str(p)])
                o = rdflib.Literal(terms['terms'][str(o)])
                graph.add((s, p, o))

            end = time.time()
            samples.append(end - start)

        return samples

class ParquetUnsorted(Format):
    def size(self) -> int:
        return os.path.getsize('terms.parquet') + os.path.getsize('triples.parquet') + os.path.getsize('data.json')

    def encoding_time(self) -> List[float]:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)

        samples = []
        for _ in range(0, self.N_RUNS):
            start = time.time()
            idTerms = {}
            triples = []

            for s, p, o in graph:
                idTerms.update({str(FarmHash32(s)): s})
                idTerms.update({str(FarmHash32(p)): p})
                idTerms.update({str(FarmHash32(o)): o})
                triples.append((FarmHash32(s), FarmHash32(p), FarmHash32(o)))

            termDataframe = pd.DataFrame({
                "terms": idTerms
            })

            tripleDataframe = pd.DataFrame({
                "triples": triples
            })

            termsTable = pa.Table.from_pandas(termDataframe, preserve_index=True)
            triplesTable = pa.Table.from_pandas(tripleDataframe)

            pq.write_table(termsTable, "terms.parquet")
            pq.write_table(triplesTable, "triples.parquet")

            end = time.time()
            samples.append(end - start)

        return samples

    def decoding_time(self) -> List[float]:
        graph = rdflib.Graph()
        graph.parse(self.graph_file)

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

            end = time.time()
            samples.append(end - start)

        return samples

results: List[pd.DataFrame] = [
    NTriples(graph_file='graphs/bldg1.ttl', name='NTriples').run(),
    Turtle(graph_file='graphs/bldg1.ttl', name='Turtle').run(),
    JSONLD(graph_file='graphs/bldg1.ttl', name='JSON-LD').run(),
    RDFXML(graph_file='graphs/bldg1.ttl', name='RDF-XML').run(),
    ParquetSorted(graph_file='graphs/bldg1.ttl', name='Parquet-Sorted').run(),
    ParquetUnsorted(graph_file='graphs/bldg1.ttl', name='Parquet-Unsorted').run(),
]

# clean up files
os.remove('data.json')
os.remove('terms.parquet')
os.remove('triples.parquet')
os.remove('terms_sorted.parquet')
os.remove('triples_sorted.parquet')

# 1 dataframe with all benchmarks
all_results = pd.concat(results, axis=0)

# export to csv so it can be used in a notebook
all_results.to_csv('results.csv', sep=',', index=False)
