from __future__ import print_function
import sys
import random
import Pyro4


if sys.version_info < (3, 0):
    input = raw_input


uri = input("Enter the URI of the server object: ")

with Pyro4.Proxy(uri) as proxy:
    print("currently allocated resources:", proxy.list())
    name1 = hex(random.randint(0, 999999))[-4:]
    name2 = hex(random.randint(0, 999999))[-4:]
    print("allocating resource...", name1)
    proxy.allocate(name1)
    print("allocating resource...", name2)
    proxy.allocate(name2)
    input("\nhit Enter now to continue normally or ^C/break to abort the connection forcefully:")
    print("free resources normally...")
    proxy.free(name1)
    proxy.free(name2)
    print("allocated resources:", proxy.list())


print("done.")
