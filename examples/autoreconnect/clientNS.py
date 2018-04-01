from __future__ import print_function
import time

import Pyro4


print("Autoreconnect using Name Server.")

# We create a proxy with a PYRONAME uri.
# That allows Pyro to look up the object again in the NS when
# it needs to reconnect later.
obj = Pyro4.core.Proxy("PYRONAME:example.autoreconnect")

while True:
    print("call...")
    try:
        obj.method(42)
        print("Sleeping 1 second")
        time.sleep(1)
    except Pyro4.errors.ConnectionClosedError:  # or possibly CommunicationError
        print("Connection lost. REBINDING...")
        print("(restart the server now)")
        obj._pyroReconnect()
