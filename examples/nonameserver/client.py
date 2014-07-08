# Client that doesn't use the Name Server. Uses URI directly.

from __future__ import print_function
import sys

import Pyro4


if sys.version_info < (3, 0):
    input = raw_input

uri = input("Enter the URI of the quote object: ")
quotegen = Pyro4.core.Proxy(uri)
print("Getting some quotes...")
print(quotegen.quote())
print(quotegen.quote())
