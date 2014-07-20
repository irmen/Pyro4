from __future__ import print_function
import Pyro4
import sys
import bench


if sys.version_info < (3, 0):
    input = raw_input

host = input("Hostname to bind on? ").strip()

obj = bench.bench()
daemon = Pyro4.Daemon(host=host)
uri = daemon.register(obj, "example.benchmark")
print("Server running, uri = %s" % uri)
daemon.requestLoop()
