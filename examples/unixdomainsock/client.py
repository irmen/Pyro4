from __future__ import print_function
import sys

import Pyro4


if sys.version_info < (3, 0):
    input = raw_input

uri = input("enter the server uri: ").strip()
with Pyro4.Proxy(uri) as p:
    response = p.message("Hello there!")
    print("Response was:", response)
