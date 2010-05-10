from __future__ import with_statement
import unittest
import Pyro.config
import Pyro.core
import threading, time

# tests that require a running Pyro server (daemon)

class MyThing(object):
    def __init__(self):
        self.dictionary={"number":42}
    def getDict(self):
        return self.dictionary
    def multiply(self,x,y):
        return x*y
    def ping(self):
        pass

class DaemonLoopThread(threading.Thread):
    def __init__(self, pyrodaemon):
        super(DaemonLoopThread,self).__init__()
        self.daemon=True
        self.pyrodaemon=pyrodaemon
        self.running=threading.Event()
        self.running.clear()
    def run(self):
        self.running.set()
        self.pyrodaemon.requestLoop()
        
class ServerTests(unittest.TestCase):
    def setUp(self):
        self.daemon=Pyro.core.Daemon(port=0)
        obj=MyThing()
        self.daemon.register(obj, "something")
        self.objectUri1=self.daemon.uriFor(obj,pyroloc=False)
        self.objectUri2=self.daemon.uriFor(obj,pyroloc=True)
        self.daemonthread=DaemonLoopThread(self.daemon)
        self.daemonthread.start()
        self.daemonthread.running.wait()
    def tearDown(self):
        time.sleep(0.05)
        self.daemon.shutdown()
        self.daemonthread.join()

    def testNoDottedNames(self):
        Pyro.config.DOTTEDNAMES=False
        with Pyro.core.Proxy(self.objectUri1) as p:
            self.assertEqual(55,p.multiply(5,11))
            x=p.getDict()
            self.assertEqual({"number":42}, x)
            try:
                p.dictionary.update({"more":666})     # should fail with DOTTEDNAMES=False (the default)
                self.fail("expected AttributeError")
            except AttributeError:
                pass
            x=p.getDict()
            self.assertEqual({"number":42}, x)

    def testDottedNames(self):
        Pyro.config.DOTTEDNAMES=True
        with Pyro.core.Proxy(self.objectUri1) as p:
            self.assertEqual(55,p.multiply(5,11))
            x=p.getDict()
            self.assertEqual({"number":42}, x)
            p.dictionary.update({"more":666})    # updating it remotely should work with DOTTEDNAMES=True
            x=p.getDict()
            self.assertEqual({"number":42, "more":666}, x)  # eek, it got updated!
        Pyro.config.DOTTEDNAMES=False

    def testConnectionStuff(self):
        p1=Pyro.core.Proxy(self.objectUri1)
        p2=Pyro.core.Proxy(self.objectUri2)
        self.assertTrue(p1._pyroConnection is None)
        self.assertTrue(p2._pyroConnection is None)
        p1.ping()
        p2.ping()
        x=p1.multiply(11,5)
        x=p2.multiply(11,5)
        self.assertTrue(p1._pyroConnection is not None)
        self.assertTrue(p2._pyroConnection is not None)
        p1._pyroRelease()
        p1._pyroRelease()
        p2._pyroRelease()
        p2._pyroRelease()
        self.assertTrue(p1._pyroConnection is None)
        self.assertTrue(p2._pyroConnection is None)
        p1._pyroBind()
        x=p1.multiply(11,5)
        x=p2.multiply(11,5)
        self.assertTrue(p1._pyroConnection is not None)
        self.assertTrue(p2._pyroConnection is not None)
        self.assertEqual("PYRO",p1._pyroUri.protocol)
        self.assertEqual("PYROLOC",p2._pyroUri.protocol)
        self.assertNotEqual(p1._pyroUri, p2._pyroUri)
        p1._pyroRelease()
        p2._pyroRelease()

    def testReconnect(self):
        with Pyro.core.Proxy(self.objectUri1) as p:
            self.assertTrue(p._pyroConnection is None)
            p._pyroReconnect(tries=100)
            self.assertTrue(p._pyroConnection is not None)
        self.assertTrue(p._pyroConnection is None)
    
    def testOneway(self):
        with Pyro.core.Proxy(self.objectUri1) as p:
            self.assertEquals(55, p.multiply(5,11))
            p._pyroOneway.add("multiply")
            self.assertEquals(None, p.multiply(5,11))
            p._pyroOneway.remove("multiply")
            self.assertEquals(55, p.multiply(5,11))

    def testSerializeConnected(self):
        # online serialization tests
        ser=Pyro.util.Serializer()
        proxy=Pyro.core.Proxy(self.objectUri1)
        proxy._pyroBind()
        self.assertFalse(proxy._pyroConnection is None)
        p,_=ser.serialize(proxy)
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
        proxy._pyroRelease()
        proxy2._pyroRelease()
        proxy3._pyroRelease()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
