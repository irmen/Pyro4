#
#   The banks server
#

from __future__ import print_function
import Pyro4.core
import Pyro4.naming
import banks

with Pyro4.core.Daemon() as daemon:
    with Pyro4.naming.locateNS() as ns:
        uri = daemon.register(banks.Rabobank)
        ns.register("example.banks.rabobank", uri)
        uri = daemon.register(banks.ABN)
        ns.register("example.banks.abn", uri)
        print("available banks:")
        print(list(ns.list(prefix="example.banks.").keys()))

    # enter the service loop.
    print("Banks are ready for customers.")
    daemon.requestLoop()
