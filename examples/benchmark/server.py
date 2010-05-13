#!/usr/bin/env python
import Pyro.core
import Pyro.naming
import bench

obj=bench.bench()

daemon=Pyro.core.Daemon()
ns=Pyro.naming.locateNS()
print "ns found at",ns._pyroUri
daemon.register(obj)
ns.remove("test.benchmark")
ns.register("test.benchmark", daemon.uriFor(obj))
print "server starting"
daemon.requestLoop()
