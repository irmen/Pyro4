import Pyro.util
import Pyro.naming

try:
	ns=Pyro.naming.locateNS("localhost")
	ns.lookup("unknown_object")
except:
	print "".join(Pyro.util.getPyroTraceback())
