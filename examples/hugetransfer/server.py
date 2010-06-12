import sys, os
import Pyro

Pyro.config.COMMTIMEOUT=2


class Testclass(object):
    def transfer(self,data):
        print("received %d bytes" % len(data))
        return len(data)

daemon=Pyro.core.Daemon()
obj=Testclass()
uri = daemon.register(obj)
ns=Pyro.naming.locateNS()
ns.remove("example.hugetransfer")
ns.register("example.hugetransfer", uri)
print("Server running.")
daemon.requestLoop()
