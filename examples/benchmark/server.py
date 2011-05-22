import Pyro4
import bench

obj=bench.bench()
daemon=Pyro4.Daemon()
uri = daemon.register(obj,"test.benchmark")
print("Server running, uri = %s" % uri)
daemon.requestLoop()
