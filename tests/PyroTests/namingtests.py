import unittest
import time
import Pyro.naming
import Pyro.config
import threading

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
        
class NSLookupTests(unittest.TestCase):

    def setUp(self):
        self.nsdaemon=Pyro.naming.NameServerDaemon(host="localhost")
        self.nsdaemonthread=NSDaemonThread(self.nsdaemon)
        self.nsdaemonthread.start()
        self.nsdaemonthread.started.wait()

    def tearDown(self):
        self.nsdaemon.shutdown()
        self.nsdaemonthread.join()

    def testLookup(self):
        self.assertRaises(NotImplementedError, Pyro.naming.locateNS)
        ns=Pyro.naming.locateNS("localhost")
        self.assertTrue(isinstance(ns, Pyro.core.Proxy))
        uri=ns._pyroUri
        self.assertEqual("PYRO",uri.protocol)
        self.assertEqual("localhost",uri.host)
        self.assertEqual(Pyro.config.DEFAULT_NS_PORT,uri.port)
        ns=Pyro.naming.locateNS("localhost:"+str(Pyro.config.DEFAULT_NS_PORT))
        uri=ns._pyroUri
        self.assertEqual("PYRO",uri.protocol)
        self.assertEqual("localhost",uri.host)
        self.assertEqual(Pyro.config.DEFAULT_NS_PORT,uri.port)
        
        self.assertRaises(NotImplementedError, Pyro.naming.locateNS, "./p:pipename")
        #ns=Pyro.naming.locateNS("./p:pipename")
        #uri=ns._pyroUri
        #self.assertEqual("PYRO",uri.protocol)
        #self.assertEqual("pipename",uri.pipename)

    def testResolve(self):
        resolved1=Pyro.naming.resolve(Pyro.core.PyroURI("PYRO:12345@host.com"))
        resolved2=Pyro.naming.resolve("PYRO:12345@host.com")
        self.assertTrue(type(resolved1) is Pyro.core.PyroURI)
        self.assertEqual(resolved1, resolved2)
        self.assertEqual("PYRO:12345@host.com:"+str(Pyro.config.DEFAULT_PORT), str(resolved1))
        
        uri=Pyro.naming.resolve("PYROLOC:"+Pyro.constants.NAMESERVER_NAME+"@localhost:"+str(Pyro.config.DEFAULT_NS_PORT))
        self.assertEqual("PYRO",uri.protocol)
        self.assertEqual("localhost",uri.host)
        self.assertNotEqual(Pyro.constants.NAMESERVER_NAME,uri.object)
        
        ns=Pyro.naming.locateNS("localhost")
        self.assertEqual(uri, ns._pyroUri)
        
        uri=Pyro.naming.resolve("PYRONAME:"+Pyro.constants.NAMESERVER_NAME+"@localhost")
        self.assertEqual("PYRO",uri.protocol)
        self.assertEqual("localhost",uri.host)
        self.assertNotEqual(Pyro.constants.NAMESERVER_NAME,uri.object)
        self.assertEqual(uri, ns._pyroUri)

        # these test still crash the server
        #uri=Pyro.naming.resolve("PYRONAME:unknown_object@localhost")

        self.assertRaises(NotImplementedError, Pyro.naming.resolve, "PYRONAME:objectname" )
        self.assertRaises(TypeError, Pyro.naming.resolve, 999)  #wrong arg type

    def testRegisterEtc(self):
        ns=Pyro.naming.locateNS("localhost")
        ns.ping()
        ns.register("test.object1",Pyro.core.PyroURI("PYRO:111111@host.com"))
        ns.register("test.object2",Pyro.core.PyroURI("PYRO:222222@host.com"))
        ns.register("test.object3",Pyro.core.PyroURI("PYRO:333333@host.com"))
        ns.register("test.sub.objectA",Pyro.core.PyroURI("PYRO:AAAAAA@host.com"))
        ns.register("test.sub.objectB",Pyro.core.PyroURI("PYRO:BBBBBB@host.com"))
        
        #this will crash the server for now
        #ns.lookup("unknown_object")
        
        uri=ns.lookup("test.object3")
        self.assertEqual(Pyro.core.PyroURI("PYRO:333333@host.com"), uri)
        ns.remove("unknown_object")
        ns.remove("test.object1")
        ns.remove("test.object2")
        ns.remove("test.object3")
        all=ns.list()
        self.assertEqual(3, len(all))  # nameserver itself + 2 leftover objects

        # do a few proxy tests because they depend on a running daemon too
        nsLocation="%s:%d" %("localhost", Pyro.config.DEFAULT_NS_PORT)
        daemonUri="PYROLOC:"+Pyro.constants.DAEMON_LOCALNAME+"@"+nsLocation
        p1=Pyro.core.Proxy(daemonUri)
        p2=Pyro.core.Proxy(daemonUri)
        self.assertTrue(p1._pyroConnection is None)
        self.assertTrue(p2._pyroConnection is None)
        p1.ping()
        p2.ping()
        x=p1.registeredObjects()
        x=p2.registeredObjects()
        self.assertTrue(p1._pyroConnection is not None)
        self.assertTrue(p2._pyroConnection is not None)
        p1._pyroRelease()
        p1._pyroRelease()
        p2._pyroRelease()
        p2._pyroRelease()
        self.assertTrue(p1._pyroConnection is None)
        self.assertTrue(p2._pyroConnection is None)
        p1._pyroBind()
        x=p1.registeredObjects()
        x=p2.registeredObjects()
        self.assertTrue(p1._pyroConnection is not None)
        self.assertTrue(p2._pyroConnection is not None)
        self.assertNotEqual(p1._pyroUri, p2._pyroUri)
        self.assertEqual("PYRO",p1._pyroUri.protocol)
        self.assertEqual("PYROLOC",p2._pyroUri.protocol)
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
