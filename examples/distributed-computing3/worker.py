from __future__ import print_function
import os
import socket
import sys
from math import sqrt
import Pyro4
import Pyro4.socketutil


if sys.version_info < (3, 0):
    range = xrange   # make sure to use the memory efficient range generator


class Worker(object):
    @Pyro4.expose
    def factorize(self, n):
        print("factorize request received for", n)
        result = self._factorize(n)
        print("    -->", result)
        return result

    def _factorize(self, n):
        """simple algorithm to find the prime factorials of the given number n"""

        def isPrime(n):
            return not any(x for x in range(2, int(sqrt(n)) + 1) if n % x == 0)

        primes = []
        candidates = range(2, n + 1)
        candidate = 2
        while not primes and candidate in candidates:
            if n % candidate == 0 and isPrime(candidate):
                primes = primes + [candidate] + self._factorize(n // candidate)
            candidate += 1
        return primes


with Pyro4.Daemon(host=Pyro4.socketutil.getIpAddress(None)) as daemon:
    # create a unique name for this worker (otherwise it overwrites other workers in the name server)
    worker_name = "Worker_%d@%s" % (os.getpid(), socket.gethostname())
    print("Starting up worker", worker_name)
    uri = daemon.register(Worker)
    with Pyro4.locateNS() as ns:
        ns.register(worker_name, uri, metadata={"example3.worker.factorizer"})
    daemon.requestLoop()
