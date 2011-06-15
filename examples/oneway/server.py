from __future__ import print_function
import time
import Pyro4

# set the oneway behavior to run inside a new thread, otherwise the client stalls.
# this is the default, but I've added it here just for clarification.
Pyro4.config.ONEWAY_THREADED=True

class Server(object):
    def __init__(self):
        self.busy=False
    def start(self, duration):
        print("start request received. Starting work...")
        self.busy=True
        for i in range(duration):
            time.sleep(1)
            print(duration-i)
        print("work is done!")
        self.busy=False
    def ready(self):
        print("ready status requested (%r)" % (not self.busy))
        return not self.busy
    def result(self):
        return "The result :)"
    def nothing(self):
        print("nothing got called, doing nothing")


######## main program

daemon=Pyro4.core.Daemon()
obj=Server()
uri=daemon.register(obj)
ns=Pyro4.naming.locateNS()
ns.register("example.oneway", uri)
print("Server is ready.")
daemon.requestLoop()
