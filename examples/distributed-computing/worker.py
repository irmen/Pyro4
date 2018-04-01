from __future__ import print_function
import os
import socket
import sys
from math import sqrt
import Pyro4
from Pyro4.util import SerializerBase
from workitem import Workitem


# For 'workitem.Workitem' we register a deserialization hook to be able to get these back from Pyro
SerializerBase.register_dict_to_class("workitem.Workitem", Workitem.from_dict)

if sys.version_info < (3, 0):
    range = xrange   # make sure to use the memory efficient range generator

WORKERNAME = "Worker_%d@%s" % (os.getpid(), socket.gethostname())


def factorize(n):
    """simple algorithm to find the prime factorials of the given number n"""

    def isPrime(n):
        return not any(x for x in range(2, int(sqrt(n)) + 1) if n % x == 0)

    primes = []
    candidates = range(2, n + 1)
    candidate = 2
    while not primes and candidate in candidates:
        if n % candidate == 0 and isPrime(candidate):
            primes = primes + [candidate] + factorize(n // candidate)
        candidate += 1
    return primes


def process(item):
    print("factorizing %s -->" % item.data)
    sys.stdout.flush()
    item.result = factorize(int(item.data))
    print(item.result)
    item.processedBy = WORKERNAME


def main():
    dispatcher = Pyro4.core.Proxy("PYRONAME:example.distributed.dispatcher")
    print("This is worker %s" % WORKERNAME)
    print("getting work from dispatcher.")
    while True:
        try:
            item = dispatcher.getWork()
        except ValueError:
            print("no work available yet.")
        else:
            process(item)
            dispatcher.putResult(item)


if __name__ == "__main__":
    main()
