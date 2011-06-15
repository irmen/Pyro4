from __future__ import print_function
import Pyro4
import excep

ns=Pyro4.naming.locateNS()
daemon=Pyro4.core.Daemon()
obj=excep.TestClass()
uri=daemon.register(obj)
ns.register("example.exceptions", uri)
print("Server started.")
daemon.requestLoop()
