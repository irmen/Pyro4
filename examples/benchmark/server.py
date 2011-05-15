import Pyro4
import bench

if not Pyro4.config.HMAC_KEY:
    Pyro4.config.HMAC_KEY="testbenchmarkkey"

obj=bench.bench()
daemon=Pyro4.Daemon()
uri = daemon.register(obj,"test.benchmark")
print("Server running, uri = %s" % uri)
daemon.requestLoop()
