# autoreconnect using the Name Server

import time
import Pyro.naming
import Pyro.core
import Pyro.errors

print "Autoreconnect using Name Server."

class TestClass(object):
    def method(self,arg):
        print "Method called with",arg
        print "You can now try to stop this server with ctrl-C/ctrl-Break"
        time.sleep(1)

obj=TestClass()
daemon = Pyro.core.Daemon()

# if we reconnect the object, it has to have the same objectId as before.
# for this example, we rely on the Name Server registration to get our old id back.

ns=Pyro.naming.locateNS()
try:
    existing=ns.lookup("test.autoreconnect")
    print "Object still exists in Name Server with id:",existing.object
    # register the object in the daemon with the old objectId
    daemon.register(obj, objectId=existing.object)
except Pyro.errors.NamingError:
    # register the object in the daemon and let it get a new objectId
    # also need to register in name server because it's not there yet.
    daemon.register(obj)
    ns.register("test.autoreconnect", daemon.uriFor(obj))
print "Server started."
daemon.requestLoop()
