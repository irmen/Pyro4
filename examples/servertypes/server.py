import time
import sys
import Pyro
from Pyro import threadutil

if sys.version_info<(3,0):
    input=raw_input
    current_thread=threadutil.currentThread
else:
    current_thread=threadutil.current_thread

class Server(object):
    def __init__(self):
        self.callcount=0
    def reset(self):
        self.callcount=0
    def getcount(self):
        return self.callcount   # the number of completed calls
    def getconfig(self):
        return Pyro.config.asDict()
    def delay(self):
        threadname=current_thread().getName()
        print("delay called in thread %s" % threadname)
        time.sleep(1)
        self.callcount+=1
        return threadname
    def onewaydelay(self):
        threadname=current_thread().getName()
        print("onewaydelay called in thread %s" % threadname)
        time.sleep(1)
        self.callcount+=1


######## main program

Pyro.config.SERVERTYPE="undefined"
servertype=input("Servertype threaded or select (t/s)?")
if servertype=="t":
    Pyro.config.SERVERTYPE="thread"
if servertype=="s":
    Pyro.config.SERVERTYPE="select"

daemon=Pyro.core.Daemon()
obj=Server()
uri=daemon.register(obj)
ns=Pyro.naming.locateNS()
ns.remove("example.servertypes")
ns.register("example.servertypes", uri)
print("Server is ready.")
daemon.requestLoop()
