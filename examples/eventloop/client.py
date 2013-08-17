from __future__ import print_function
import Pyro4
import sys

if sys.version_info<(3,0):
    input=raw_input


with Pyro4.core.Proxy("PYRONAME:example.embedded.server") as proxy:
    print("5*11=%d" % proxy.multiply(5,11))
    print("'x'*10=%s" % proxy.multiply('x',10))

    input("press enter to do two more calls:")
    print("2*4=%d" % proxy.multiply(2,4))
    print("'@'*3=%s" % proxy.multiply('@',3))
