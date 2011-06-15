from __future__ import print_function
import Pyro4
import bench

obj=bench.bench()
daemon=Pyro4.Daemon()
uri = daemon.register(obj,"example.benchmark")
print("Server running, uri = %s" % uri)
daemon.requestLoop()
