# This is the code that visits the warehouse.
from __future__ import print_function
import sys
import Pyro4
from person import Person

if sys.version_info<(3,0):
    input=raw_input

def main():
    uri=input("Enter the uri of the warehouse: ").strip()
    warehouse=Pyro4.Proxy(uri)
    janet=Person("Janet")
    henry=Person("Henry")
    janet.visit(warehouse)
    henry.visit(warehouse)

if __name__=="__main__":
    main()
