import Pyro
import excep

ns=Pyro.naming.locateNS()
daemon=Pyro.core.Daemon()
obj=excep.TestClass()
uri=daemon.register(obj)
ns.remove("example.exceptions")
ns.register("example.exceptions", uri)
print("Server started.")
daemon.requestLoop()
