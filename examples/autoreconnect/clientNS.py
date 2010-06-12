import time
import Pyro

print("Autoreconnect using Name Server.")

# We create a proxy with a PYRONAME uri.
# That allows Pyro to look up the object again in the NS when
# it needs to reconnect later.
obj=Pyro.core.Proxy("PYRONAME:example.autoreconnect")

while True:
    print("call...")
    try:
        obj.method(42)
        print("Sleeping 1 second")
        time.sleep(1)
    except Pyro.errors.ConnectionClosedError:     # or possibly even ProtocolError
        print("Connection lost. REBINDING...")
        print("(restart the server now)")
        obj._pyroReconnect()
