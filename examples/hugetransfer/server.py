from __future__ import print_function
import Pyro4

#Pyro4.config.COMMTIMEOUT=2


class Testclass(object):
    def transfer(self,data):
        print("received %d bytes" % len(data))
        return len(data)

daemon=Pyro4.core.Daemon()
obj=Testclass()
uri = daemon.register(obj)
ns=Pyro4.naming.locateNS()
ns.register("example.hugetransfer", uri)
print("Server running.")
daemon.requestLoop()
