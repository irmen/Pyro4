"""
Tests for the name server (online/running).

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import unittest
import time
import Pyro4.core
import Pyro4.naming
import Pyro4.socketutil
import Pyro4.constants
from Pyro4.errors import NamingError
from Pyro4 import threadutil
from testsupport import *


class NSLoopThread(threadutil.Thread):
    def __init__(self, nameserver):
        super(NSLoopThread,self).__init__()
        self.setDaemon(True)
        self.nameserver=nameserver
        self.running=threadutil.Event()
        self.running.clear()
    def run(self):
        self.running.set()
        self.nameserver.requestLoop()

class BCSetupTests(unittest.TestCase):
    def setUp(self):
        Pyro4.config.HMAC_KEY=tobytes("testsuite")
    def tearDown(self):
        Pyro4.config.HMAC_KEY=None
    def testBCstart(self):
        myIpAddress=Pyro4.socketutil.getMyIpAddress(workaround127=True)
        nsUri, nameserver, bcserver = Pyro4.naming.startNS(host=myIpAddress, port=0, bcport=0, enableBroadcast=False)
        self.assertTrue(bcserver is None)
        nameserver.close()
        nsUri, nameserver, bcserver = Pyro4.naming.startNS(host=myIpAddress, port=0, bcport=0, enableBroadcast=True)
        self.assertTrue(bcserver is not None, "expected a BC server to be running. Check DNS setup (hostname must not resolve to loopback address")
        self.assertTrue(bcserver.fileno() > 1)
        self.assertTrue(bcserver.sock is not None)
        nameserver.close()
        bcserver.close()


#This test is disabled because otherwise the suite won't succeed if you have a name server running somewhere:
#class NameServerNotRunningTests(unittest.TestCase):
#    def testLocate(self):
#        Pyro4.config.HMAC_KEY=tobytes("testsuite")
#        self.assertRaises(NamingError, Pyro4.naming.locateNS)
#        Pyro4.config.HMAC_KEY=None


class NameServerTests(unittest.TestCase):
    def setUp(self):
        Pyro4.config.POLLTIMEOUT=0.1
        Pyro4.config.HMAC_KEY=tobytes("testsuite")
        myIpAddress=Pyro4.socketutil.getMyIpAddress(workaround127=True)
        self.nsUri, self.nameserver, self.bcserver = Pyro4.naming.startNS(host=myIpAddress, port=0, bcport=0)
        self.assertTrue(self.bcserver is not None,"expected a BC server to be running")
        self.bcserver.runInThread()
        self.daemonthread=NSLoopThread(self.nameserver)
        self.daemonthread.start()
        self.daemonthread.running.wait()
        self.old_bcPort=Pyro4.config.NS_BCPORT
        self.old_nsPort=Pyro4.config.NS_PORT
        self.old_nsHost=Pyro4.config.NS_HOST
        Pyro4.config.NS_PORT=self.nsUri.port
        Pyro4.config.NS_HOST=myIpAddress
        Pyro4.config.NS_BCPORT=self.bcserver.getPort()
    def tearDown(self):
        time.sleep(0.01)
        self.nameserver.shutdown()
        self.bcserver.close()
        self.daemonthread.join()
        Pyro4.config.HMAC_KEY=None
        Pyro4.config.NS_HOST=self.old_nsHost
        Pyro4.config.NS_PORT=self.old_nsPort
        Pyro4.config.NS_BCPORT=self.old_bcPort
   
    def testLookupAndRegister(self):
        ns=Pyro4.naming.locateNS() # broadcast lookup
        self.assertTrue(isinstance(ns, Pyro4.core.Proxy))
        ns._pyroRelease()
        ns=Pyro4.naming.locateNS(self.nsUri.host) # normal lookup
        self.assertTrue(isinstance(ns, Pyro4.core.Proxy))
        uri=ns._pyroUri
        self.assertEqual("PYRO",uri.protocol)
        self.assertEqual(self.nsUri.host,uri.host)
        self.assertEqual(Pyro4.config.NS_PORT,uri.port)
        ns._pyroRelease()
        ns=Pyro4.naming.locateNS(self.nsUri.host,Pyro4.config.NS_PORT)
        uri=ns._pyroUri
        self.assertEqual("PYRO",uri.protocol)
        self.assertEqual(self.nsUri.host,uri.host)
        self.assertEqual(Pyro4.config.NS_PORT,uri.port)
        
        # check that we cannot register a stupid type
        self.assertRaises(TypeError, ns.register, "unittest.object1", 5555)
        # we can register str or URI, lookup always returns URI        
        ns.register("unittest.object2", "PYRO:55555@host.com:4444")
        self.assertEqual(Pyro4.core.URI("PYRO:55555@host.com:4444"), ns.lookup("unittest.object2"))
        ns.register("unittest.object3", Pyro4.core.URI("PYRO:66666@host.com:4444"))
        self.assertEqual(Pyro4.core.URI("PYRO:66666@host.com:4444"), ns.lookup("unittest.object3"))
        ns._pyroRelease()

    def testDaemonPyroObj(self):
        uri=self.nsUri
        uri.object=Pyro4.constants.DAEMON_NAME
        with Pyro4.core.Proxy(uri) as daemonobj:
            daemonobj.ping()
            daemonobj.registered()
            try:
                daemonobj.shutdown()
                self.fail("should not succeed to call unexposed method on daemon")
            except AttributeError:
                pass
        
    def testMulti(self):
        uristr=str(self.nsUri)
        p=Pyro4.core.Proxy(uristr)
        p._pyroBind()
        p._pyroRelease()
        uri=Pyro4.naming.resolve(uristr)
        p=Pyro4.core.Proxy(uri)
        p._pyroBind()
        p._pyroRelease()
        uri=Pyro4.naming.resolve(uristr)
        p=Pyro4.core.Proxy(uri)
        p._pyroBind()
        p._pyroRelease()
        uri=Pyro4.naming.resolve(uristr)
        p=Pyro4.core.Proxy(uri)
        p._pyroBind()
        p._pyroRelease()
        uri=Pyro4.naming.resolve(uristr)
        p=Pyro4.core.Proxy(uri)
        p._pyroBind()
        p._pyroRelease()
        uri=Pyro4.naming.resolve(uristr)
        p=Pyro4.core.Proxy(uri)
        p._pyroBind()
        p._pyroRelease()
        daemonUri="PYRO:"+Pyro4.constants.DAEMON_NAME+"@"+uri.location
        _=Pyro4.naming.resolve(daemonUri)
        _=Pyro4.naming.resolve(daemonUri)
        _=Pyro4.naming.resolve(daemonUri)
        _=Pyro4.naming.resolve(daemonUri)
        _=Pyro4.naming.resolve(daemonUri)
        _=Pyro4.naming.resolve(daemonUri)
        uri=Pyro4.naming.resolve(daemonUri)
        pyronameUri="PYRONAME:"+Pyro4.constants.NAMESERVER_NAME+"@"+uri.location
        _=Pyro4.naming.resolve(pyronameUri)
        _=Pyro4.naming.resolve(pyronameUri)
        _=Pyro4.naming.resolve(pyronameUri)
        _=Pyro4.naming.resolve(pyronameUri)
        _=Pyro4.naming.resolve(pyronameUri)
        _=Pyro4.naming.resolve(pyronameUri)
    
    def testResolve(self):
        resolved1=Pyro4.naming.resolve(Pyro4.core.URI("PYRO:12345@host.com:4444"))
        resolved2=Pyro4.naming.resolve("PYRO:12345@host.com:4444")
        self.assertTrue(type(resolved1) is Pyro4.core.URI)
        self.assertEqual(resolved1, resolved2)
        self.assertEqual("PYRO:12345@host.com:4444", str(resolved1))
        
        ns=Pyro4.naming.locateNS(self.nsUri.host, self.nsUri.port)
        uri=Pyro4.naming.resolve("PYRONAME:"+Pyro4.constants.NAMESERVER_NAME+"@"+self.nsUri.host+":"+str(self.nsUri.port))
        self.assertEqual("PYRO",uri.protocol)
        self.assertEqual(self.nsUri.host,uri.host)
        self.assertEqual(Pyro4.constants.NAMESERVER_NAME,uri.object)
        self.assertEqual(uri, ns._pyroUri)
        ns._pyroRelease()

        # broadcast lookup
        self.assertRaises(NamingError, Pyro4.naming.resolve, "PYRONAME:unknown_object")
        uri=Pyro4.naming.resolve("PYRONAME:"+Pyro4.constants.NAMESERVER_NAME)
        self.assertEqual(Pyro4.core.URI,type(uri))
        self.assertEqual("PYRO",uri.protocol)

        # test some errors
        self.assertRaises(NamingError, Pyro4.naming.resolve, "PYRONAME:unknown_object@"+self.nsUri.host)
        self.assertRaises(TypeError, Pyro4.naming.resolve, 999)  #wrong arg type


    def testRefuseDottedNames(self):
        with Pyro4.naming.locateNS(self.nsUri.host, self.nsUri.port) as ns:
            # the name server should never have dotted names enabled
            self.assertRaises(AttributeError, ns.namespace.keys)
            self.assertTrue(ns._pyroConnection is not None)
        self.assertTrue(ns._pyroConnection is None)


class NameServerTests0000(unittest.TestCase):
    def setUp(self):
        Pyro4.config.POLLTIMEOUT=0.1
        Pyro4.config.HMAC_KEY=tobytes("testsuite")
        self.nsUri, self.nameserver, self.bcserver = Pyro4.naming.startNS(host="", port=0, bcport=0)
        self.assertEqual("0.0.0.0", self.nsUri.host, "for hostname \"\" the resulting ip must be 0.0.0.0")
        self.assertTrue(self.bcserver is not None,"expected a BC server to be running")
        self.bcserver.runInThread()
        self.old_bcPort=Pyro4.config.NS_BCPORT
        self.old_nsPort=Pyro4.config.NS_PORT
        self.old_nsHost=Pyro4.config.NS_HOST
        Pyro4.config.NS_PORT=self.nsUri.port
        Pyro4.config.NS_HOST=self.nsUri.host
        Pyro4.config.NS_BCPORT=self.bcserver.getPort()
    def tearDown(self):
        time.sleep(0.01)
        self.nameserver.shutdown()
        self.bcserver.close()
        Pyro4.config.NS_HOST=self.old_nsHost
        Pyro4.config.NS_PORT=self.old_nsPort
        Pyro4.config.NS_BCPORT=self.old_bcPort
        Pyro4.config.HMAC_KEY=None

    def testBCLookup0000(self):
        ns=Pyro4.naming.locateNS()  # broadcast lookup
        self.assertTrue(isinstance(ns, Pyro4.core.Proxy))
        self.assertNotEqual("0.0.0.0", ns._pyroUri.host, "returned location must not be 0.0.0.0 when running on 0.0.0.0")
        ns._pyroRelease()


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
