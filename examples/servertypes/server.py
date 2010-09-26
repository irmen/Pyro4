import time
import Pyro4
from Pyro4 import threadutil

class Server(object):
    def __init__(self):
        self.callcount=0
    def reset(self):
        self.callcount=0
    def getcount(self):
        return self.callcount   # the number of completed calls
    def getconfig(self):
        return Pyro4.config.asDict()
    def delay(self):
        threadname=threadutil.currentThread().getName()
        print "delay called in thread",threadname
        time.sleep(1)
        self.callcount+=1
        return threadname
    def onewaydelay(self):
        threadname=threadutil.currentThread().getName()
        print "onewaydelay called in thread",threadname
        time.sleep(1)
        self.callcount+=1


######## main program

Pyro4.config.SERVERTYPE="undefined"
servertype=raw_input("Servertype threaded or select (t/s)?")
if servertype=="t":
    Pyro4.config.SERVERTYPE="thread"
if servertype=="s":
    Pyro4.config.SERVERTYPE="select"

daemon=Pyro4.core.Daemon()
obj=Server()
uri=daemon.register(obj)
ns=Pyro4.naming.locateNS()
ns.remove("example.servertypes")
ns.register("example.servertypes", uri)
print "Server is ready."
daemon.requestLoop()
