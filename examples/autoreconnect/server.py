# autoreconnect PYRO version

import time
import Pyro.core

print "Autoreconnect using PYRO uri."

class TestClass(object):
    def method(self,arg):
        print "Method called with",arg
        print "You can now try to stop this server with ctrl-C/ctrl-Break"
        time.sleep(1)

obj=TestClass()
daemon = Pyro.core.Daemon()

# We are responsible to (re)connect objects with the same object Id,
# so that the client can reuse its PYRO-uri directly to reconnect.
# There are a few options, such as depending on the Name server to
# maintain a name registration for our object (see the serverNS for this).
# Or we could store our objects in our own persistent database.
# But for this example we will just use a pre-generated id.
# I used the following command to create it:
#    python -c "import uuid; print uuid.uuid4().hex"

FIXED_OBJECTID="6e060e3a53164a96a28d03f7acbdff26"
daemon.register(obj,objectId=FIXED_OBJECTID)

print "Server started, uri =",daemon.uriFor(obj)
daemon.requestLoop()
