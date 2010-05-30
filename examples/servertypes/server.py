#!/usr/bin/env python
import time, threading, sys
import Pyro

if sys.version_info<(3,0):
    input=raw_input

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
        threadname=threading.currentThread().getName()
        print("delay called in thread %s" % threadname)
        time.sleep(1)
        self.callcount+=1
        return threadname
    def onewaydelay(self):
        threadname=threading.currentThread().getName()
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
