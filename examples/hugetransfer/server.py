#!/usr/bin/env python
import sys, os
import Pyro.core
import Pyro.naming
import Pyro.config

Pyro.config.COMMTIMEOUT=2


class Testclass(object):
    def transfer(self,data):
        print 'received',len(data),'bytes'
        return len(data)

daemon=Pyro.core.Daemon()
obj=Testclass()
uri = daemon.register(obj)
ns=Pyro.naming.locateNS()
print "ns found at",ns._pyroUri
ns.remove("test.hugetransfer")
ns.register("test.hugetransfer", uri)
print "Server running."
daemon.requestLoop()

