# autoreconnect PYROLOC version
import time
import Pyro.core
import Pyro.errors
import Pyro.config

print "Autoreconnect using PYROLOC uri."

# We create a proxy with a PYROLOC uri.
# That allows Pyro to look up the object again by name when it needs to reconnect later.
obj=Pyro.core.Proxy("PYROLOC:test.autoreconnect.pyroloc@"+Pyro.config.HOST)

while True:
    print "call..."
    try:
        obj.method(42)
        print "Sleeping 1 second"
        time.sleep(1)
    except Pyro.errors.ConnectionClosedError,x:     # or possibly even ProtocolError
        print "Connection lost. REBINDING..."
        print "(restart the server now)"
        obj._pyroReconnect()
