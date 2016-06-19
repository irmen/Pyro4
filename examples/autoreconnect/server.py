from __future__ import print_function
import time
import Pyro4

print("Autoreconnect using PYRO uri.")


@Pyro4.expose
class TestClass(object):
    def method(self, arg):
        print("Method called with %s" % arg)
        print("You can now try to stop this server with ctrl-C/ctrl-Break")
        time.sleep(1)


# We are responsible to (re)connect objects with the same object Id,
# so that the client can reuse its PYRO-uri directly to reconnect.
# There are a few options, such as depending on the Name server to
# maintain a name registration for our object (see the serverNS for this).
# Or we could store our objects in our own persistent database.
# But for this example we will just use a pre-generated id (fixed name).
# The other thing is that your Daemon must re-bind on the same port.
# By default Pyro will select a random port so we specify a fixed port.

with Pyro4.core.Daemon(port=7777) as daemon:
    uri = daemon.register(TestClass, objectId="example.autoreconnect_fixed_objectid")
    print("Server started, uri: %s" % uri)
    daemon.requestLoop()
