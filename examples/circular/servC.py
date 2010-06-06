import Pyro
import chain

this = "C"
next = "A"

servername="example.chain."+this

daemon=Pyro.core.Daemon()
obj=chain.Chain(this,next)
uri=daemon.register(obj)
ns=Pyro.naming.locateNS()
ns.remove(servername)
ns.register(servername,uri)

# enter the service loop.
print 'Server started',this
daemon.requestLoop()
