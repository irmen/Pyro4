#!/usr/bin/env python
import Pyro.core
import Pyro.naming
import time

class Server(object):
    def __init__(self):
        self.busy=False
    def start(self):
        print "start request received. Starting work..."
        self.busy=True
        for i in range(10):
            time.sleep(1)
            print 10-i
        print "work is done!"
        self.busy=False
    def ready(self):
        print "ready status requested (%r)" % (not self.busy)
        return not self.busy
    def result(self):
        return "The result :)"
    def nothing(self):
        return "nothing got called, doing nothing"
      

######## main program

daemon=Pyro.core.Daemon()
obj=Server()
uri=daemon.register(obj)
ns=Pyro.naming.locateNS()
ns.remove("test.oneway")
ns.register("test.oneway", uri)
print "Server is ready."
daemon.requestLoop()
