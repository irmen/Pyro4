#!/usr/bin/env python

# Client that doesn't use the Name Server. Uses URI directly.

import sys
import Pyro

if sys.version_info<(3,0):
    input=raw_input

uri = input('Enter the URI of the quote object: ')
quotegen=Pyro.core.Proxy(uri)
print("Getting some quotes...")
print(quotegen.quote())
print(quotegen.quote())
