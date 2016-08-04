from __future__ import print_function
import time
import Pyro4

print("Autoreconnect using Name Server.")


@Pyro4.expose
class TestClass(object):
    def method(self, arg):
        print("Method called with %s" % arg)
        print("You can now try to stop this server with ctrl-C/ctrl-Break")
        time.sleep(1)


# If we reconnect the object, it has to have the same objectId as before.
# for this example, we rely on the Name Server registration to get our old id back.
# If we KNOW 100% that PYRONAME-uris are the only thing used to access our
# object, we could skip all this and just register as usual.
# That works because the proxy, when reconnecting, will do a new nameserver lookup
# and receive the new object uri back. This REQUIRES:
#   - clients will never connect using a PYRO-uri
#   - client proxy._pyroBind() is never called
# BUT for sake of example, and because we really cannot guarantee the above,
# here we go for the safe route and reuse our previous object id.

ns = Pyro4.naming.locateNS()
try:
    existing = ns.lookup("example.autoreconnect")
    print("Object still exists in Name Server with id: %s" % existing.object)
    print("Previous daemon socket port: %d" % existing.port)
    # start the daemon on the previous port
    daemon = Pyro4.core.Daemon(port=existing.port)
    # register the object in the daemon with the old objectId
    daemon.register(TestClass, objectId=existing.object)
except Pyro4.errors.NamingError:
    print("There was no previous registration in the name server.")
    # just start a new daemon on a random port
    daemon = Pyro4.core.Daemon()
    # register the object in the daemon and let it get a new objectId
    # also need to register in name server because it's not there yet.
    uri = daemon.register(TestClass)
    ns.register("example.autoreconnect", uri)

print("Server started.")
daemon.requestLoop()

# note: we are not removing the name server registration when terminating!
