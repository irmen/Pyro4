from __future__ import print_function
import time
import sys
import Pyro4
from Pyro4 import threadutil

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
        return Pyro4.config.asDict()
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

Pyro4.config.SERVERTYPE="undefined"
servertype=input("Servertype threaded or multiplex (t/m)?")
if servertype=="t":
    Pyro4.config.SERVERTYPE="thread"
else:
    Pyro4.config.SERVERTYPE="multiplex"

daemon=Pyro4.core.Daemon()
obj=Server()
uri=daemon.register(obj)
ns=Pyro4.naming.locateNS()
ns.register("example.servertypes", uri)
print("Server is ready.")
daemon.requestLoop()
