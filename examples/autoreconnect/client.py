from __future__ import print_function
import time
import sys
import Pyro4

if sys.version_info<(3,0):
    input=raw_input

print("Autoreconnect using PYRO uri.")

# We create a proxy with a PYRO uri.
# Reconnect logic depends on the server now.
# (it needs to restart the object with the same id)
uri=input("Enter the uri that the server printed:").strip()
obj=Pyro4.core.Proxy(uri)

while True:
    print("call...")
    try:
        obj.method(42)
        print("Sleeping 1 second")
        time.sleep(1)
    except Pyro4.errors.ConnectionClosedError:     # or possibly even ProtocolError
        print("Connection lost. REBINDING...")
        print("(restart the server now)")
        obj._pyroReconnect()
