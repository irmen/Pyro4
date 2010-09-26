import Pyro4
import bench

obj=bench.bench()

daemon=Pyro4.core.Daemon()
ns=Pyro4.naming.locateNS()
print "ns found at",ns._pyroUri
uri = daemon.register(obj)
ns.remove("example.benchmark")
ns.register("example.benchmark", uri)
print "Server running."
daemon.requestLoop()
