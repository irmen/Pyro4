from __future__ import print_function, division
import sys
import Pyro4
import Pyro4.util

if sys.version_info < (3, 0):
    input = raw_input

sys.excepthook = Pyro4.util.excepthook


uri = input("Enter streaming server uri: ").strip()
with Pyro4.Proxy(uri) as p:
    print("\nnormal list:")
    print(p.list())
    print("\nvia iterator:")
    print(list(p.iterator()))
    print("\nvia generator:")
    print(list(p.generator()))
    print("\nslow generator:")
    for number in p.slow_generator():
        print(number)
