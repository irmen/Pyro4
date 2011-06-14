from __future__ import print_function
import time
import Pyro4

print("Autoreconnect using Name Server.")

class TestClass(object):
    def method(self,arg):
        print("Method called with %s" % arg)
        print("You can now try to stop this server with ctrl-C/ctrl-Break")
        time.sleep(1)

obj=TestClass()

# if we reconnect the object, it has to have the same objectId as before.
# for this example, we rely on the Name Server registration to get our old id back.

ns=Pyro4.naming.locateNS()
try:
    existing=ns.lookup("example.autoreconnect")
    print("Object still exists in Name Server with id: %s" % existing.object)
    print("Previous daemon socket port: %d" % existing.port)
    # start the daemon on the previous port
    daemon = Pyro4.core.Daemon(port=existing.port)
    # register the object in the daemon with the old objectId
    daemon.register(obj, objectId=existing.object)
except Pyro4.errors.NamingError:
    # just start a new daemon on a random port
    daemon = Pyro4.core.Daemon()
    # register the object in the daemon and let it get a new objectId
    # also need to register in name server because it's not there yet.
    uri = daemon.register(obj)
    ns.register("example.autoreconnect", uri)
print("Server started.")
daemon.requestLoop()

# note: we are not removing the name server registration!
