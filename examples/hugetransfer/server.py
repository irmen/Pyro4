#!/usr/bin/env python
import sys, os
import Pyro.core
import Pyro.naming
import socket
socket.setdefaulttimeout(3)

class Testclass(object):
	def transfer(self,data):
		print 'received',len(data),'bytes'
		return len(data)


daemon=Pyro.core.Daemon()
obj=Testclass()
daemon.register(obj)
ns=Pyro.naming.locateNS()
ns.remove("test.hugetransfer")
ns.register("test.hugetransfer", daemon.uriFor(obj))
print "Server running."
daemon.requestLoop()



