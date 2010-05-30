from __future__ import with_statement
import unittest
import Pyro.config
import Pyro.core
import Pyro.errors
import threading, time, os, sys

# tests that require a running Pyro server (daemon)
# the server part here is not using a timeout setting.

class MyThing(object):
    def __init__(self):
        self.dictionary={"number":42}
    def getDict(self):
        return self.dictionary
    def multiply(self,x,y):
        return x*y
    def ping(self):
        pass
    def delay(self, delay):
        time.sleep(delay)
        return "slept %d seconds" % delay
    def delayAndId(self, delay, id):
        time.sleep(delay)
        return "slept for "+str(id)
    def testargs(self,x,*args,**kwargs):
        return x,args,kwargs

class DaemonLoopThread(threading.Thread):
    def __init__(self, pyrodaemon):
        super(DaemonLoopThread,self).__init__()
        self.setDaemon(True)
        self.pyrodaemon=pyrodaemon
        self.running=threading.Event()
        self.running.clear()
    def run(self):
        self.running.set()
        self.pyrodaemon.requestLoop()
        
class ServerTestsThreadNoTimeout(unittest.TestCase):
    SERVERTYPE="thread"
    COMMTIMEOUT=None
    def setUp(self):
        Pyro.config.POLLTIMEOUT=0.1
        Pyro.config.SERVERTYPE=self.SERVERTYPE
        Pyro.config.COMMTIMEOUT=self.COMMTIMEOUT
        self.old_workerthreads=Pyro.config.WORKERTHREADS
        Pyro.config.WORKERTHREADS=10
        self.daemon=Pyro.core.Daemon(port=0)
        obj=MyThing()
        uri=self.daemon.register(obj, "something")
        self.objectUri=uri
        self.daemonthread=DaemonLoopThread(self.daemon)
        self.daemonthread.start()
        self.daemonthread.running.wait()
    def tearDown(self):
        time.sleep(0.05)
        self.daemon.shutdown()
        self.daemonthread.join()
        Pyro.config.SERVERTYPE="thread"
        Pyro.config.COMMTIMEOUT=None
        Pyro.config.WORKERTHREADS=self.old_workerthreads

    def testNoDottedNames(self):
        Pyro.config.DOTTEDNAMES=False
        with Pyro.core.Proxy(self.objectUri) as p:
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
            # also test some argument type things
            self.assertEqual((1,(),{}), p.testargs(1))
            self.assertEqual((1,(2,3),{'a':4}), p.testargs(1,2,3,a=4))
            self.assertEqual((1,(),{'a':2}), p.testargs(1, **{'a':2}))
            if sys.version_info>=(2,6):
                result=p.testargs(1, **{unichr(0x20ac):2})
                key=result[2].keys()[0]
                self.assertTrue(key==unichr(0x20ac))


    def testDottedNames(self):
        try:
            Pyro.config.DOTTEDNAMES=True
            with Pyro.core.Proxy(self.objectUri) as p:
                self.assertEqual(55,p.multiply(5,11))
                x=p.getDict()
                self.assertEqual({"number":42}, x)
                p.dictionary.update({"more":666})    # updating it remotely should work with DOTTEDNAMES=True
                x=p.getDict()
                self.assertEqual({"number":42, "more":666}, x)  # eek, it got updated!
        finally:
            Pyro.config.DOTTEDNAMES=False

    def testConnectionStuff(self):
        p1=Pyro.core.Proxy(self.objectUri)
        p2=Pyro.core.Proxy(self.objectUri)
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
        self.assertEqual("PYRO",p2._pyroUri.protocol)
        p1._pyroRelease()
        p2._pyroRelease()

    def testCompression(self):
        try:
            with Pyro.core.Proxy(self.objectUri) as p:
                Pyro.config.COMPRESSION=True
                self.assertEqual(55, p.multiply(5,11))
                self.assertEqual("*"*1000, p.multiply("*"*500,2))
        finally:
            Pyro.config.COMPRESSION=False

    def testReconnect(self):
        with Pyro.core.Proxy(self.objectUri) as p:
            self.assertTrue(p._pyroConnection is None)
            p._pyroReconnect(tries=100)
            self.assertTrue(p._pyroConnection is not None)
        self.assertTrue(p._pyroConnection is None)
    
    def testOneway(self):
        with Pyro.core.Proxy(self.objectUri) as p:
            self.assertEquals(55, p.multiply(5,11))
            p._pyroOneway.add("multiply")
            self.assertEquals(None, p.multiply(5,11))
            self.assertEquals(None, p.multiply(5,11))
            self.assertEquals(None, p.multiply(5,11))
            p._pyroOneway.remove("multiply")
            self.assertEquals(55, p.multiply(5,11))
            self.assertEquals(55, p.multiply(5,11))
            self.assertEquals(55, p.multiply(5,11))
            # check nonexisting method behavoir
            self.assertRaises(AttributeError, p.nonexisting)
            p._pyroOneway.add("nonexisting")
            # now it shouldn't fail because of oneway semantics
            p.nonexisting()
            
    def testOnewayDelayed(self):
        try:
            with Pyro.core.Proxy(self.objectUri) as p:
                p.ping()
                Pyro.config.ONEWAY_THREADED=True   # the default
                p._pyroOneway.add("delay")
                now=time.time()
                p.delay(1)  # oneway so we should continue right away
                self.assertTrue(time.time()-now < 0.2, "delay should be running as oneway")
                now=time.time()
                self.assertEquals(55,p.multiply(5,11), "expected a normal result from a non-oneway call")
                self.assertTrue(time.time()-now < 0.2, "delay should be running in its own thread")
                # make oneway calls run in the server thread
                # we can change the config here and the server will pick it up on the fly
                Pyro.config.ONEWAY_THREADED=False   
                now=time.time()
                p.delay(1)  # oneway so we should continue right away
                self.assertTrue(time.time()-now < 0.2, "delay should be running as oneway")
                now=time.time()
                self.assertEquals(55,p.multiply(5,11), "expected a normal result from a non-oneway call")
                self.assertFalse(time.time()-now < 0.2, "delay should be running in the server thread")
        finally:
            Pyro.config.ONEWAY_THREADED=True   # back to normal

    def testOnewayOnClass(self):
        class ProxyWithOneway(Pyro.core.Proxy):
            def __init__(self, arg):
                super(ProxyWithOneway,self).__init__(arg)
                self._pyroOneway=["multiply"]   # set is faster but don't care for this test
        with ProxyWithOneway(self.objectUri) as p:
            self.assertEquals(None, p.multiply(5,11))
            p._pyroOneway=[]   # empty set is better but don't care in this test
            self.assertEquals(55, p.multiply(5,11))

    def testSerializeConnected(self):
        # online serialization tests
        ser=Pyro.util.Serializer()
        proxy=Pyro.core.Proxy(self.objectUri)
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

    def testTimeoutCall(self):
        Pyro.config.COMMTIMEOUT=None
        with Pyro.core.Proxy(self.objectUri) as p:
            p.ping()
            start=time.time()
            p.delay(0.5)
            duration=time.time()-start
            self.assertAlmostEqual(0.5, duration, 1)
            p._pyroTimeout=0.1
            start=time.time()
            self.assertRaises(Pyro.errors.TimeoutError, p.delay, 1)
            duration=time.time()-start
            if sys.platform!="cli":
                self.assertAlmostEqual(0.1, duration, 1)
            else:
                # ironpython's time is wonky
                self.assertTrue(0.0<duration<0.7)

    def testTimeoutConnect(self):
        # set up a unresponsive daemon
        with Pyro.core.Daemon(port=0) as d:
            time.sleep(0.5)
            obj=MyThing()
            uri=d.register(obj)
            # we're not going to start the daemon's event loop
            p=Pyro.core.Proxy(uri)
            p._pyroTimeout=0.2
            start=time.time()
            self.assertRaises(Pyro.errors.TimeoutError, p.ping)
            duration=time.time()-start
            self.assertTrue(duration<2.0)
            
    def testProxySharing(self):
        class SharedProxyThread(threading.Thread):
            def __init__(self, proxy):
                super(SharedProxyThread,self).__init__()
                self.proxy=proxy
                self.terminate=False
                self.error=True
                self.setDaemon(True)
            def run(self):
                try:
                    while not self.terminate:
                        reply=self.proxy.multiply(5,11)
                        assert reply==55
                        time.sleep(0.001)
                    self.error=False
                except:
                    print "Something went wrong in the thread (SharedProxyThread):"
                    print "".join(Pyro.util.getPyroTraceback())
        with Pyro.core.Proxy(self.objectUri) as p:
            threads=[]
            for i in range(5):
                t=SharedProxyThread(p)
                threads.append(t)
                t.start()
            time.sleep(1)
            for t in threads:
                t.terminate=True
                t.join()
            for t in threads:
                self.assertFalse(t.error, "all threads should report no errors") 

    def testServerParallelism(self):
        class ClientThread(threading.Thread):
            def __init__(self, uri, name):
                super(ClientThread,self).__init__()
                self.setDaemon(True)
                self.proxy=Pyro.core.Proxy(uri)
                self.name=name
                self.error=True
            def run(self):
                try:
                    reply=self.proxy.delayAndId(0.5, self.name)
                    assert reply=="slept for "+self.name
                    self.error=False
                finally:
                    self.proxy._pyroRelease()
        threads=[]
        start=time.time()
        for i in range(6):
            t=ClientThread(self.objectUri,"t%d" % i)
            threads.append(t)
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            self.assertFalse(t.error, "all threads should report no errors")
        del threads
        duration=time.time()-start
        if Pyro.config.SERVERTYPE=="select":
            # select based server doesn't execute calls in parallel,
            # so 6 threads times 0.5 seconds =~ 3 seconds
            self.assertTrue(2.5<duration<3.5)
        else:
            # thread based server does execute calls in parallel,
            # so 6 threads taking 0.5 seconds =~ 0.5 seconds passed
            self.assertTrue(0.3<duration<0.7)

if os.name!="java":
    class ServerTestsSelectNoTimeout(ServerTestsThreadNoTimeout):
        SERVERTYPE="select"
        COMMTIMEOUT=None

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
