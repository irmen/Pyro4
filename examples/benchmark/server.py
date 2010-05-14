#!/usr/bin/env python
import Pyro.core
import Pyro.naming
import bench

obj=bench.bench()

daemon=Pyro.core.Daemon()
ns=Pyro.naming.locateNS()
print "ns found at",ns._pyroUri
uri = daemon.register(obj)
ns.remove("test.benchmark")
ns.register("test.benchmark", uri)
print "Server running."
daemon.requestLoop()
