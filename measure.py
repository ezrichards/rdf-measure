# Measurement apparatus for RDF encodings
import sys

file_name = input("Specify the file to measure: ")
print("File name is: " + file_name)

try:
    file = open(file_name)
except OSError:
    print("Could not open file: " + file_name)
    sys.exit()

with file:
    lines = file.readlines()

    for line in lines: 
        print(line)