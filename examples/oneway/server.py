import time
import Pyro

# set the oneway behavior to run inside a new thread, otherwise the client stalls.
# this is the default, but I've added it here just for clarification.
Pyro.config.ONEWAY_THREADED=True

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

daemon=Pyro.core.Daemon()
obj=Server()
uri=daemon.register(obj)
ns=Pyro.naming.locateNS()
ns.remove("example.oneway")
ns.register("example.oneway", uri)
print("Server is ready.")
daemon.requestLoop()
