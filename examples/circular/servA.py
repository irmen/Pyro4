import Pyro4
import chain

this = "A"
next = "B"

servername="example.chain."+this

daemon=Pyro4.core.Daemon()
obj=chain.Chain(this,next)
uri=daemon.register(obj)
ns=Pyro4.naming.locateNS()
ns.remove(servername)
ns.register(servername,uri)

# enter the service loop.
print 'Server started',this
daemon.requestLoop()
