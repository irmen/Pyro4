from __future__ import print_function
import Pyro4
import chain

this = "B"
next = "C"

servername="example.chain."+this

daemon=Pyro4.core.Daemon()
obj=chain.Chain(this,next)
uri=daemon.register(obj)
ns=Pyro4.naming.locateNS()
ns.register(servername,uri)

# enter the service loop.
print("Server started %s" % this)
daemon.requestLoop()
