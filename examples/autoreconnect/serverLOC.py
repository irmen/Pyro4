# autoreconnect PYROLOC version

import time
import Pyro.core

print "Autoreconnect using PYROLOC uri."

class TestClass(object):
    def method(self,arg):
        print "Method called with",arg
        print "You can now try to stop this server with ctrl-C/ctrl-Break"
        time.sleep(1)

obj=TestClass()
daemon = Pyro.core.Daemon()

# just register the object, no need to take care of old objectIds,
# because the client will just reconnect using the object name.
daemon.register(obj,"test.autoreconnect.pyroloc")

print "Server started, uri =",daemon.uriFor(obj,pyroloc=True)
daemon.requestLoop()
