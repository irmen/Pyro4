from __future__ import print_function
import logging
import sys
import Pyro4


# initialize the logger so you can see what is happening with the callback exception message:
logging.basicConfig(stream=sys.stderr, format="[%(asctime)s,%(name)s,%(levelname)s] %(message)s")
log = logging.getLogger("Pyro4")
log.setLevel(logging.WARNING)


class CallbackHandler(object):
    def crash(self):
        a = 1
        b = 0
        return a // b

    @Pyro4.expose
    def call1(self):
        print("\n\ncallback 1 received from server!")
        print("going to crash - you won't see the exception here, only on the server")
        return self.crash()

    @Pyro4.expose
    @Pyro4.callback
    def call2(self):
        print("\n\ncallback 2 received from server!")
        print("going to crash - but you will see the exception here too")
        return self.crash()


daemon = Pyro4.core.Daemon()
callback = CallbackHandler()
daemon.register(callback)

with Pyro4.core.Proxy("PYRONAME:example.callback2") as server:
    server.doCallback(callback)   # this is a oneway call, so we can continue right away

print("waiting for callbacks to arrive...")
print("(ctrl-c/break the program once it's done)")
daemon.requestLoop()
