import unittest
import Pyro.config
import Pyro.naming
from Pyro.errors import *
import threading, socket

# online name server tests

class OnlineTests(unittest.TestCase):
    # These tests actually use a running name server.
    # They also include a few tests that are not strictly name server tests,
    # but just tests of some stuff that requires a working Pyro server.
    
    def assertNameServerRunning(self):
        try:
            ns=Pyro.naming.locateNS()
        except PyroError:
            print "Can't find a name server"
            self.fail("No name server found. You need to have a name server running (+broadcast server) on the default ports, to be able to run these tests")
        else:
            self.hostname=ns._pyroUri.host
            objs=ns.list(prefix="unittest.")
            for name in objs:
                ns.remove(name)
        return

          
    def testLookupAndRegister(self):
        self.assertNameServerRunning()
        ns=Pyro.naming.locateNS() # broadcast lookup
        self.assertTrue(isinstance(ns, Pyro.core.Proxy))
        ns=Pyro.naming.locateNS(self.hostname) # normal lookup
        self.assertTrue(isinstance(ns, Pyro.core.Proxy))
        uri=ns._pyroUri
        self.assertEqual("PYRO",uri.protocol)
        self.assertEqual(self.hostname,uri.host)
        self.assertEqual(Pyro.config.NS_PORT,uri.port)
        ns=Pyro.naming.locateNS(self.hostname,Pyro.config.NS_PORT)
        uri=ns._pyroUri
        self.assertEqual("PYRO",uri.protocol)
        self.assertEqual(self.hostname,uri.host)
        self.assertEqual(Pyro.config.NS_PORT,uri.port)
        
        # check that we cannot register a stupid type
        self.assertRaises(TypeError, ns.register, "unittest.object1", 5555)
        # we can register str or PyroURI, lookup always returns PyroURI        
        ns.register("unittest.object2", "PYRO:55555@host.com")
        self.assertEquals(Pyro.core.PyroURI("PYRO:55555@host.com"), ns.lookup("unittest.object2"))
        ns.register("unittest.object3", Pyro.core.PyroURI("PYRO:66666@host.com"))
        self.assertEquals(Pyro.core.PyroURI("PYRO:66666@host.com"), ns.lookup("unittest.object3"))
        
        # check that the non-socket locations are not yet supported        
        self.assertRaises(NotImplementedError, Pyro.naming.locateNS, "./p:pipename")
        #ns=Pyro.naming.locateNS("./p:pipename")
        #uri=ns._pyroUri
        #self.assertEqual("PYRO",uri.protocol)
        #self.assertEqual("pipename",uri.pipename)

    def testResolve(self):
        self.assertNameServerRunning()
        resolved1=Pyro.naming.resolve(Pyro.core.PyroURI("PYRO:12345@host.com"))
        resolved2=Pyro.naming.resolve("PYRO:12345@host.com")
        self.assertTrue(type(resolved1) is Pyro.core.PyroURI)
        self.assertEqual(resolved1, resolved2)
        self.assertEqual("PYRO:12345@host.com:"+str(Pyro.config.PORT), str(resolved1))
        
        uri=Pyro.naming.resolve("PYROLOC:"+Pyro.constants.NAMESERVER_NAME+"@"+self.hostname+":"+str(Pyro.config.NS_PORT))
        self.assertEqual("PYRO",uri.protocol)
        self.assertEqual(self.hostname,uri.host)
        self.assertNotEqual(Pyro.constants.NAMESERVER_NAME,uri.object)
        
        ns=Pyro.naming.locateNS(self.hostname)
        self.assertEqual(uri, ns._pyroUri)
        
        uri=Pyro.naming.resolve("PYRONAME:"+Pyro.constants.NAMESERVER_NAME+"@"+self.hostname)
        self.assertEqual("PYRO",uri.protocol)
        self.assertEqual(self.hostname,uri.host)
        self.assertNotEqual(Pyro.constants.NAMESERVER_NAME,uri.object)
        self.assertEqual(uri, ns._pyroUri)

        # broadcast lookup
        self.assertRaises(NamingError, Pyro.naming.resolve, "PYRONAME:unknown_object")
        uri=Pyro.naming.resolve("PYRONAME:"+Pyro.constants.NAMESERVER_NAME)
        self.assertEquals(Pyro.core.PyroURI,type(uri))
        self.assertEquals("PYRO",uri.protocol)

        # test some errors
        self.assertRaises(NamingError, Pyro.naming.resolve, "PYRONAME:unknown_object@"+self.hostname)
        self.assertRaises(TypeError, Pyro.naming.resolve, 999)  #wrong arg type

    def testOnlineStuff(self):
        self.assertNameServerRunning()
        # do a few proxy tests because they depend on a running daemon too
        nsLocation="%s:%d" %(self.hostname, Pyro.config.NS_PORT)
        daemonUri="PYROLOC:"+Pyro.constants.DAEMON_LOCALNAME+"@"+nsLocation
        p1=Pyro.core.Proxy(daemonUri)
        p2=Pyro.core.Proxy(daemonUri)
        self.assertTrue(p1._pyroConnection is None)
        self.assertTrue(p2._pyroConnection is None)
        p1.ping()
        p2.ping()
        x=p1.registered()
        x=p2.registered()
        self.assertTrue(p1._pyroConnection is not None)
        self.assertTrue(p2._pyroConnection is not None)
        p1._pyroRelease()
        p1._pyroRelease()
        p2._pyroRelease()
        p2._pyroRelease()
        self.assertTrue(p1._pyroConnection is None)
        self.assertTrue(p2._pyroConnection is None)
        p1._pyroBind()
        x=p1.registered()
        x=p2.registered()
        self.assertTrue(p1._pyroConnection is not None)
        self.assertTrue(p2._pyroConnection is not None)
        self.assertNotEqual(p1._pyroUri, p2._pyroUri)
        self.assertEqual("PYRO",p1._pyroUri.protocol)
        self.assertEqual("PYROLOC",p2._pyroUri.protocol)
        
    def testSerCoreOnline(self):
        self.assertNameServerRunning()
        # online serialization tests
        ser=Pyro.util.Serializer()
        nsLocation="%s:%d" %(self.hostname, Pyro.config.NS_PORT)
        daemonUri="PYROLOC:"+Pyro.constants.DAEMON_LOCALNAME+"@"+nsLocation
        proxy=Pyro.core.Proxy(daemonUri)
        proxy._pyroBind()
        self.assertFalse(proxy._pyroConnection is None)
        p=ser.serialize(proxy)
        proxy2=ser.deserialize(p)
        self.assertTrue(proxy2._pyroConnection is None)
        self.assertFalse(proxy._pyroConnection is None)
        self.assertEqual(proxy2._pyroUri, proxy._pyroUri)
        self.assertEqual(proxy2._pyroSerializer, proxy._pyroSerializer)
        proxy2._pyroBind()
        self.assertFalse(proxy2._pyroConnection is None)
        self.assertFalse(proxy2._pyroConnection is proxy._pyroConnection)
        proxy._pyroRelease()
        proxy2._pyroRelease()
        self.assertTrue(proxy._pyroConnection is None)
        self.assertTrue(proxy2._pyroConnection is None)
        proxy.ping()
        proxy2.ping()
        # try copying a connected proxy
        import copy
        proxy3=copy.copy(proxy)
        self.assertTrue(proxy3._pyroConnection is None)
        self.assertFalse(proxy._pyroConnection is None)
        self.assertEqual(proxy3._pyroUri, proxy._pyroUri)
        self.assertFalse(proxy3._pyroUri is proxy._pyroUri)
        self.assertEqual(proxy3._pyroSerializer, proxy._pyroSerializer)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
