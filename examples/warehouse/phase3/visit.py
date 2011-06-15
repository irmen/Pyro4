# This is the code that visits the warehouse.
from __future__ import print_function
import sys
import Pyro4
import Pyro4.util
from person import Person

sys.excepthook=Pyro4.util.excepthook

def main():
    warehouse=Pyro4.Proxy("PYRONAME:example.warehouse")
    janet=Person("Janet")
    henry=Person("Henry")
    janet.visit(warehouse)
    henry.visit(warehouse)

if __name__=="__main__":
    main()
