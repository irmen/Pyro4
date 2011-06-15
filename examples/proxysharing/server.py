from __future__ import print_function
import time
import Pyro4

class RemoteObject(object):
    def __init__(self):
        self.amount=0
    def method(self, arg):
        return " ~~this is the remote result~~ "
    def work(self):
        print("work... %d" %self.amount)
        time.sleep(0.5)
        self.amount+=1
    def reset_work(self):
        self.amount=0
    def get_work_done(self):
        return self.amount

ns=Pyro4.naming.locateNS()
daemon=Pyro4.core.Daemon()
obj=RemoteObject()
uri=daemon.register(obj)
ns.register("example.proxysharing", uri)
print("Server is ready.")
daemon.requestLoop()
