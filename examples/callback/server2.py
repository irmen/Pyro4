from __future__ import with_statement
import Pyro4

class CallbackServer(object):
    def doCallback(self, callback):
        print("server: doing callback 1 to client")
        try:
            callback.call1()
        except:
            print("got an exception from the callback.")
            print("".join(Pyro4.util.getPyroTraceback()))
        print("server: doing callback 2 to client")
        try:
            callback.call2()
        except:
            print("got an exception from the callback.")
            print("".join(Pyro4.util.getPyroTraceback()))
        print("server: callbacks done")

with Pyro4.core.Daemon() as daemon:
    with Pyro4.naming.locateNS() as ns:
        obj=CallbackServer()
        uri=daemon.register(obj)
        ns.register("example.callback2",uri)
    print("Server ready.")
    daemon.requestLoop()
