from __future__ import print_function
import sys

import Pyro4


if sys.version_info < (3, 0):
    input = raw_input

with Pyro4.core.Proxy("PYRONAME:example.embedded.server") as proxy:
    print("5*11=%d" % proxy.multiply(5, 11))
    print("'x'*10=%s" % proxy.multiply('x', 10))

    input("press enter to do a loop of some more calls:")
    for i in range(1, 20):
        print("2*i=%d" % proxy.multiply(2, i))
        print("'@'*i=%s" % proxy.multiply('@', i))
