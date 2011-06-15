from __future__ import with_statement
import time
import Pyro4

class Worker(object):
    def __init__(self, number, callback):
        self.number=number
        self.callback=callback
        print("Worker %d created" % self.number)
    def work(self, amount):
        print("Worker %d busy..." % self.number)
        time.sleep(amount)
        print("Worker %d done. Informing callback client." % self.number)
        self._pyroDaemon.unregister(self)
        self.callback.done(self.number)    # invoke the callback object

class CallbackServer(object):
    def __init__(self):
        self.number=0
    def addworker(self, callback):
        self.number+=1
        print("server: adding worker %d" % self.number)
        worker=Worker(self.number, callback)
        self._pyroDaemon.register(worker)   # make it a Pyro object
        return worker

with Pyro4.core.Daemon() as daemon:
    with Pyro4.naming.locateNS() as ns:
        obj=CallbackServer()
        uri=daemon.register(obj)
        ns.register("example.callback",uri)
    print("Server ready.")
    daemon.requestLoop()
