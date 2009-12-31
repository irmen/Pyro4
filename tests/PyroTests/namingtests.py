import unittest
import Pyro.config
import Pyro.naming
from Pyro.errors import *
import threading, socket

class NSDaemonThread(threading.Thread):
    def __init__(self, nsdaemon):
        super(NSDaemonThread,self).__init__()
        self.nsdaemon=nsdaemon
        self.started=threading.Event()
    def run(self):
        self.started.set()
        try:
            self.nsdaemon.requestLoop()
        finally:
            self.nsdaemon.close()
    def shutdown(self):
        self.nsdaemon.shutdown()


class OnlineTests(unittest.TestCase):
    # These tests actually use a running name server.
    # They also include a few tests that are not strictly name server tests,
    # but just tests of some stuff that requires a working Pyro server.
    
    def _createServers(self):
        print "creating servers"
        Pyro.config.SERVERTYPE="select"   # threaded server cannot be aborted automatically at the moment
        Pyro.config.NS_BCPORT+=1  # some systems don't like the broadcast server rebinding on the same port
        Pyro.config.NS_PORT+=1
        self.hostname=socket.gethostname()
        self.nsdaemon=Pyro.naming.NameServerDaemon(self.hostname)
        self.nsdaemonthread=NSDaemonThread(self.nsdaemon)
        self.nsdaemonthread.start()
        self.nsdaemonthread.started.wait()
        nsUri=self.nsdaemon.uriFor(self.nsdaemon.ns)
        print "NS URI=",nsUri
        self.bcserver=Pyro.naming.BroadcastServer(nsUri,bchost=self.hostname)
        self.bcserver.daemon=True
        self.bcserver.start()
        self.bcserver.running.wait()

    def _stopServers(self):
        print "stopping servers"
        try:
            self.bcserver.close()
            self.nsdaemonthread.shutdown()
            self.nsdaemonthread.join()
        except Exception,x:
            print "Error in _stopServers",x

    def testServer(self):
        try:
            self._createServers()
            print "HOSTNAME=",self.hostname
            print "NSDAEMONTHREAD=",self.nsdaemonthread
            print "BCSERVER=",self.bcserver
        finally:
            self._stopServers()

            
    def testLookupAndRegister(self):
        try:
            self._createServers()
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
            self.assertRaises(TypeError, ns.register, "test.object1", 5555)
            # we can register str or PyroURI, lookup always returns PyroURI        
            ns.register("test.object2", "PYRO:55555@host.com")
            self.assertEquals(Pyro.core.PyroURI("PYRO:55555@host.com"), ns.lookup("test.object2"))
            ns.register("test.object3", Pyro.core.PyroURI("PYRO:66666@host.com"))
            self.assertEquals(Pyro.core.PyroURI("PYRO:66666@host.com"), ns.lookup("test.object3"))
            
            # check that the non-socket locations are not yet supported        
            self.assertRaises(NotImplementedError, Pyro.naming.locateNS, "./p:pipename")
            #ns=Pyro.naming.locateNS("./p:pipename")
            #uri=ns._pyroUri
            #self.assertEqual("PYRO",uri.protocol)
            #self.assertEqual("pipename",uri.pipename)
        finally:
            self._stopServers()

    def testResolve(self):
        try:
            self._createServers()
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
        finally:
            self._stopServers()

    def testOnlineStuff(self):
        try:
            self._createServers()
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
        finally:
            self._stopServers()
        
    def testSerCoreOnline(self):
        try:
            self._createServers()
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
        finally:
            self._stopServers()

class OfflineTests(unittest.TestCase):
    def testRegister(self):
        ns=Pyro.naming.NameServer()
        ns.ping()
        ns.register("test.object1","PYRO:111111@host.com")  # can register string or PyroURI
        ns.register("test.object2","PYRO:222222@host.com")
        ns.register("test.object3","PYRO:333333@host.com")
        ns.register("test.sub.objectA",Pyro.core.PyroURI("PYRO:AAAAAA@host.com"))
        ns.register("test.sub.objectB",Pyro.core.PyroURI("PYRO:BBBBBB@host.com"))
        
        self.assertRaises(NamingError, ns.lookup, "unknown_object")
        
        uri=ns.lookup("test.object3")
        self.assertEqual(Pyro.core.PyroURI("PYRO:333333@host.com"), uri)   # lookup always returns PyroURI
        ns.remove("unknown_object")
        ns.remove("test.object1")
        ns.remove("test.object2")
        ns.remove("test.object3")
        all=ns.list()
        self.assertEqual(2, len(all))  # 2 leftover objects
    def testList(self):
        ns=Pyro.naming.NameServer()
        ns.register("test.objects.1","SOMETHING1")
        ns.register("test.objects.2","SOMETHING2")
        ns.register("test.objects.3","SOMETHING3")
        ns.register("test.other.a","SOMETHINGA")
        ns.register("test.other.b","SOMETHINGB")
        ns.register("test.other.c","SOMETHINGC")
        ns.register("entirely.else","MEH")
        objects=ns.list()
        self.assertEqual(7,len(objects))
        objects=ns.list(prefix="nothing")
        self.assertEqual(0,len(objects))
        objects=ns.list(prefix="test.")
        self.assertEqual(6,len(objects))
        objects=ns.list(regex=r".+other..")
        self.assertEqual(3,len(objects))
        self.assertTrue("test.other.a" in objects)
        self.assertEqual("SOMETHINGA", objects["test.other.a"])
        objects=ns.list(regex=r"\d\d\d\d\d\d\d\d\d\d")
        self.assertEqual(0,len(objects))
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
