# This is the code that visits the warehouse.
import sys

import Pyro4
from person import Person


if sys.version_info < (3, 0):
    input = raw_input

uri = input("Enter the uri of the warehouse: ").strip()
warehouse = Pyro4.Proxy(uri)
janet = Person("Janet")
henry = Person("Henry")
janet.visit(warehouse)
henry.visit(warehouse)
