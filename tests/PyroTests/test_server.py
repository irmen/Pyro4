"""
Tests for a running Pyro server, without timeouts.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import unittest
import Pyro4.core
import Pyro4.errors
import Pyro4.util
import time, os, sys, platform
from Pyro4 import threadutil
from testsupport import *


class MyThing(object):
    def __init__(self):
        self.dictionary={"number":42}
    def getDict(self):
        return self.dictionary
    def multiply(self,x,y):
        return x*y
    def divide(self,x,y):
        return x//y
    def ping(self):
        pass
    def echo(self, obj):
        return obj
    def delay(self, delay):
        time.sleep(delay)
        return "slept %d seconds" % delay
    def delayAndId(self, delay, id):
        time.sleep(delay)
        return "slept for "+str(id)
    def testargs(self,x,*args,**kwargs):
        return x,args,kwargs

class MyThing2(object):
    pass

class DaemonLoopThread(threadutil.Thread):
    def __init__(self, pyrodaemon):
        super(DaemonLoopThread,self).__init__()
        self.setDaemon(True)
        self.pyrodaemon=pyrodaemon
        self.running=threadutil.Event()
        self.running.clear()
    def run(self):
        self.running.set()
        try:
            self.pyrodaemon.requestLoop()
        except:
            print("Swallow exception from terminated daemon")


class DaemonWithSabotagedHandshake(Pyro4.core.Daemon):
    def _handshake(self, conn):
        # a bit of a hack, overriding this internal method to return a CONNECTFAIL...
        data=tobytes("rigged connection failure")
        msg=Pyro4.core.MessageFactory.createMessage(Pyro4.core.MessageFactory.MSG_CONNECTFAIL, data, 0, 1)
        conn.send(msg)
        return False
    
class ServerTestsBrokenHandshake(unittest.TestCase):
    def setUp(self):
        Pyro4.config.HMAC_KEY=tobytes("testsuite")
        self.daemon=DaemonWithSabotagedHandshake(port=0)
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
        Pyro4.config.HMAC_KEY=None
    def testDaemonConnectFail(self):
        # check what happens when the daemon responds with a failed connection msg
        with Pyro4.Proxy(self.objectUri) as p:
            try:
                p.ping()
                self.fail("expected CommunicationError")
            except Pyro4.errors.CommunicationError:
                xv=sys.exc_info()[1]
                message=str(xv)
                self.assertTrue("rigged connection failure" in message)

class ServerTestsOnce(unittest.TestCase):
    """tests that are fine to run with just a single server type"""
    def setUp(self):
        Pyro4.config.HMAC_KEY=tobytes("testsuite")
        self.daemon=Pyro4.core.Daemon(port=0)
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
        Pyro4.config.HMAC_KEY=None

    def testNoDottedNames(self):
        Pyro4.config.DOTTEDNAMES=False
        with Pyro4.core.Proxy(self.objectUri) as p:
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

    def testSomeArgumentTypes(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            self.assertEqual((1,(),{}), p.testargs(1))
            self.assertEqual((1,(2,3),{'a':4}), p.testargs(1,2,3,a=4))
            self.assertEqual((1,(),{'a':2}), p.testargs(1, **{'a':2}))
            if sys.version_info>=(2,6,5):
                # python 2.6.5 and later support unicode keyword args
                self.assertEqual((1,(),{unichr(65):2}), p.testargs(1, **{unichr(65):2}))
                if platform.python_implementation()!="PyPy":
                    # PyPy doesn't accept unicode kwargs that cannot be encoded to ascii, see https://bugs.pypy.org/issue751
                    result=p.testargs(1, **{unichr(0x20ac):2})
                    key=list(result[2].keys())[0]
                    self.assertTrue(key==unichr(0x20ac))

    def testDottedNames(self):
        try:
            Pyro4.config.DOTTEDNAMES=True
            with Pyro4.core.Proxy(self.objectUri) as p:
                self.assertEqual(55,p.multiply(5,11))
                x=p.getDict()
                self.assertEqual({"number":42}, x)
                p.dictionary.update({"more":666})    # updating it remotely should work with DOTTEDNAMES=True
                x=p.getDict()
                self.assertEqual({"number":42, "more":666}, x)  # eek, it got updated!
        finally:
            Pyro4.config.DOTTEDNAMES=False

    def testNormalProxy(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            self.assertEqual(42,p.multiply(7,6))

    def testBatchProxy(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            batch=Pyro4.batch(p)
            self.assertEqual(None,batch.multiply(7,6))
            self.assertEqual(None,batch.divide(999,3))
            self.assertEqual(None,batch.ping())
            self.assertEqual(None,batch.divide(999,0))      # force an exception here
            self.assertEqual(None,batch.multiply(3,4))      # this call should not be performed after the error
            results=batch()
            self.assertEqual(42,next(results))
            self.assertEqual(333,next(results))
            self.assertEqual(None,next(results))
            self.assertRaises(ZeroDivisionError, next, results)     # 999//0 should raise this error
            self.assertRaises(StopIteration, next, results)     # no more results should be available after the error

    def testAsyncProxy(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            async=Pyro4.async(p)
            begin=time.time()
            result=async.delayAndId(1,42)
            duration=time.time()-begin
            self.assertTrue(duration<0.1)
            self.assertFalse(result.ready)
            self.assertFalse(result.wait(0.5))    # not available within 0.5 sec
            self.assertEqual("slept for 42",result.value)
            self.assertTrue(result.ready)
            self.assertTrue(result.wait())

    def testAsyncProxyCallchain(self):
        class FuncHolder(object):
            count=0
            def function(self, value, increase=1):
                self.count+=1
                return value+increase
        with Pyro4.core.Proxy(self.objectUri) as p:
            async=Pyro4.async(p)
            holder=FuncHolder()
            begin=time.time()
            result=async.multiply(2,3)
            result.then(holder.function, increase=10) \
                  .then(holder.function, increase=5) \
                  .then(holder.function)
            duration=time.time()-begin
            self.assertTrue(duration<0.1)
            value=result.value
            self.assertTrue(result.ready)
            self.assertEqual(22,value)
            self.assertEqual(3,holder.count)

    def testBatchOneway(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            batch=Pyro4.batch(p)
            self.assertEqual(None,batch.multiply(7,6))
            self.assertEqual(None,batch.delay(1))           # a delay shouldn't matter with oneway
            self.assertEqual(None,batch.multiply(3,4))
            begin=time.time()
            results=batch(oneway=True)
            duration=time.time()-begin
            self.assertTrue(duration<0.1,"oneway batch with delay should return almost immediately")
            self.assertEqual(None,results)

    def testBatchAsync(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            batch=Pyro4.batch(p)
            self.assertEqual(None,batch.multiply(7,6))
            self.assertEqual(None,batch.delay(1))           # a delay shouldn't matter with async
            self.assertEqual(None,batch.multiply(3,4))
            begin=time.time()
            asyncresult=batch(async=True)
            duration=time.time()-begin
            self.assertTrue(duration<0.1,"async batch with delay should return almost immediately")
            results=asyncresult.value
            self.assertEqual(42,next(results))
            self.assertEqual("slept 1 seconds",next(results))
            self.assertEqual(12,next(results))
            self.assertRaises(StopIteration, next, results)     # no more results should be available

    def testBatchAsyncCallchain(self):
        class FuncHolder(object):
            count=0
            def function(self, values):
                result=[value+1 for value in values]
                self.count+=1
                return result
        with Pyro4.core.Proxy(self.objectUri) as p:
            batch=Pyro4.batch(p)
            self.assertEqual(None,batch.multiply(7,6))
            self.assertEqual(None,batch.multiply(3,4))
            result=batch(async=True)
            holder=FuncHolder()
            result.then(holder.function).then(holder.function)
            value=result.value
            self.assertTrue(result.ready)
            self.assertEqual([44,14],value)
            self.assertEqual(2,holder.count)

    def testPyroTracebackNormal(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            try:
                p.divide(999,0)  # force error here
                self.fail("expected error")
            except ZeroDivisionError:
                # going to check if the magic pyro traceback attribute is available for batch methods too
                tb="".join(Pyro4.util.getPyroTraceback())
                self.assertTrue("Remote traceback:" in tb)  # validate if remote tb is present
                self.assertTrue("ZeroDivisionError" in tb)  # the error
                self.assertTrue("return x//y" in tb)  # the statement

    def testPyroTracebackBatch(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            batch=Pyro4.batch(p)
            self.assertEqual(None,batch.divide(999,0))      # force an exception here
            results=batch()
            try:
                next(results)
                self.fail("expected error")
            except ZeroDivisionError:
                # going to check if the magic pyro traceback attribute is available for batch methods too
                tb="".join(Pyro4.util.getPyroTraceback())
                self.assertTrue("Remote traceback:" in tb)  # validate if remote tb is present
                self.assertTrue("ZeroDivisionError" in tb)  # the error
                self.assertTrue("return x//y" in tb)  # the statement
            self.assertRaises(StopIteration, next, results)     # no more results should be available after the error

    def testAutoProxy(self):
        obj=MyThing2()
        try:
            with Pyro4.core.Proxy(self.objectUri) as p:
                Pyro4.config.AUTOPROXY=False   # make sure autoproxy is disabled
                result=p.echo(obj)
                self.assertTrue(isinstance(result,MyThing2))
                self.daemon.register(obj)
                result=p.echo(obj)
                self.assertTrue(isinstance(result,MyThing2), "with autoproxy off the object should be an instance of the class")
                self.daemon.unregister(obj)
                result=p.echo(obj)
                self.assertTrue(isinstance(result,MyThing2), "serialized object must still be normal object")
                Pyro4.config.AUTOPROXY=True   # make sure autoproxying is enabled
                result=p.echo(obj)
                self.assertTrue(isinstance(result,MyThing2), "non-pyro object must be returned as normal class")
                self.daemon.register(obj)
                result=p.echo(obj)
                self.assertTrue(isinstance(result, Pyro4.core.Proxy),"serialized pyro object must be a proxy")
                self.daemon.unregister(obj)
                result=p.echo(obj)
                self.assertTrue(isinstance(result,MyThing2), "unregistered pyro object must be normal class again")
                # note: the custom serializer may still be active but it should be smart enough to see
                # that the object is no longer a pyro object, and therefore, no proxy should be created.

        finally:
            Pyro4.config.AUTOPROXY=True

    def testConnectOnce(self):
        with Pyro4.core.Proxy(self.objectUri) as proxy:
            self.assertTrue(proxy._pyroBind(), "first bind should always connect")
            self.assertTrue(proxy._pyroBind(), "second bind should still connect again because it releases first")

    def testConnectingThreads(self):
        class ConnectingThread(threadutil.Thread):
            new_connections=0
            def __init__(self, proxy, event):
                threadutil.Thread.__init__(self)
                self.proxy=proxy
                self.event=event
                self.setDaemon(True)
            def run(self):
                self.event.wait()
                if self.proxy._pyroBind():
                    ConnectingThread.new_connections+=1     # 1 more new connection done
        with Pyro4.core.Proxy(self.objectUri) as proxy:
            event = threadutil.Event()
            threads = [ConnectingThread(proxy, event) for _ in range(8)]
            for t in threads:
                t.start()
            event.set()
            for t in threads:
                t.join()
            self.assertEqual(1, ConnectingThread.new_connections, "proxy shared among threads must still have only 1 connect done")


class ServerTestsThreadNoTimeout(unittest.TestCase):
    SERVERTYPE="thread"
    COMMTIMEOUT=None
    def setUp(self):
        Pyro4.config.POLLTIMEOUT=0.1
        Pyro4.config.SERVERTYPE=self.SERVERTYPE
        Pyro4.config.COMMTIMEOUT=self.COMMTIMEOUT
        Pyro4.config.THREADPOOL_MINTHREADS=2
        Pyro4.config.THREADPOOL_MAXTHREADS=20
        Pyro4.config.HMAC_KEY=tobytes("testsuite")
        self.daemon=Pyro4.core.Daemon(port=0)
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
        Pyro4.config.SERVERTYPE="thread"
        Pyro4.config.COMMTIMEOUT=None
        Pyro4.config.HMAC_KEY=None

    def testConnectionStuff(self):
        p1=Pyro4.core.Proxy(self.objectUri)
        p2=Pyro4.core.Proxy(self.objectUri)
        self.assertTrue(p1._pyroConnection is None)
        self.assertTrue(p2._pyroConnection is None)
        p1.ping()
        p2.ping()
        _=p1.multiply(11,5)
        _=p2.multiply(11,5)
        self.assertTrue(p1._pyroConnection is not None)
        self.assertTrue(p2._pyroConnection is not None)
        p1._pyroRelease()
        p1._pyroRelease()
        p2._pyroRelease()
        p2._pyroRelease()
        self.assertTrue(p1._pyroConnection is None)
        self.assertTrue(p2._pyroConnection is None)
        p1._pyroBind()
        _=p1.multiply(11,5)
        _=p2.multiply(11,5)
        self.assertTrue(p1._pyroConnection is not None)
        self.assertTrue(p2._pyroConnection is not None)
        self.assertEqual("PYRO",p1._pyroUri.protocol)
        self.assertEqual("PYRO",p2._pyroUri.protocol)
        p1._pyroRelease()
        p2._pyroRelease()

    def testReconnectAndCompression(self):
        # try reconnects
        with Pyro4.core.Proxy(self.objectUri) as p:
            self.assertTrue(p._pyroConnection is None)
            p._pyroReconnect(tries=100)
            self.assertTrue(p._pyroConnection is not None)
        self.assertTrue(p._pyroConnection is None)
        # test compression:
        try:
            with Pyro4.core.Proxy(self.objectUri) as p:
                Pyro4.config.COMPRESSION=True
                self.assertEqual(55, p.multiply(5,11))
                self.assertEqual("*"*1000, p.multiply("*"*500,2))
        finally:
            Pyro4.config.COMPRESSION=False
    
    def testOneway(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            self.assertEqual(55, p.multiply(5,11))
            p._pyroOneway.add("multiply")
            self.assertEqual(None, p.multiply(5,11))
            self.assertEqual(None, p.multiply(5,11))
            self.assertEqual(None, p.multiply(5,11))
            p._pyroOneway.remove("multiply")
            self.assertEqual(55, p.multiply(5,11))
            self.assertEqual(55, p.multiply(5,11))
            self.assertEqual(55, p.multiply(5,11))
            # check nonexisting method behavoir
            self.assertRaises(AttributeError, p.nonexisting)
            p._pyroOneway.add("nonexisting")
            # now it shouldn't fail because of oneway semantics
            p.nonexisting()
        # also test on class:
        class ProxyWithOneway(Pyro4.core.Proxy):
            def __init__(self, arg):
                super(ProxyWithOneway,self).__init__(arg)
                self._pyroOneway=["multiply"]   # set is faster but don't care for this test
        with ProxyWithOneway(self.objectUri) as p:
            self.assertEqual(None, p.multiply(5,11))
            p._pyroOneway=[]   # empty set is better but don't care in this test
            self.assertEqual(55, p.multiply(5,11))
            
    def testOnewayDelayed(self):
        try:
            with Pyro4.core.Proxy(self.objectUri) as p:
                p.ping()
                Pyro4.config.ONEWAY_THREADED=True   # the default
                p._pyroOneway.add("delay")
                now=time.time()
                p.delay(1)  # oneway so we should continue right away
                self.assertTrue(time.time()-now < 0.2, "delay should be running as oneway")
                now=time.time()
                self.assertEqual(55,p.multiply(5,11), "expected a normal result from a non-oneway call")
                self.assertTrue(time.time()-now < 0.2, "delay should be running in its own thread")
                # make oneway calls run in the server thread
                # we can change the config here and the server will pick it up on the fly
                Pyro4.config.ONEWAY_THREADED=False   
                now=time.time()
                p.delay(1)  # oneway so we should continue right away
                self.assertTrue(time.time()-now < 0.2, "delay should be running as oneway")
                now=time.time()
                self.assertEqual(55,p.multiply(5,11), "expected a normal result from a non-oneway call")
                self.assertFalse(time.time()-now < 0.2, "delay should be running in the server thread")
        finally:
            Pyro4.config.ONEWAY_THREADED=True   # back to normal

    def testSerializeConnected(self):
        # online serialization tests
        ser=Pyro4.util.Serializer()
        proxy=Pyro4.core.Proxy(self.objectUri)
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

    def testException(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            try:
                p.divide(1,0)
            except:
                et,ev,tb=sys.exc_info()
                self.assertEqual(ZeroDivisionError, et)
                pyrotb="".join(Pyro4.util.getPyroTraceback(et,ev,tb))
                self.assertTrue("Remote traceback" in pyrotb)
                self.assertTrue("ZeroDivisionError" in pyrotb)
                del tb

    def testTimeoutCall(self):
        Pyro4.config.COMMTIMEOUT=None
        with Pyro4.core.Proxy(self.objectUri) as p:
            p.ping()
            start=time.time()
            p.delay(0.5)
            duration=time.time()-start
            self.assertTrue(0.4<duration<0.6)
            p._pyroTimeout=0.1
            start=time.time()
            self.assertRaises(Pyro4.errors.TimeoutError, p.delay, 1)
            duration=time.time()-start
            if sys.platform!="cli":
                self.assertAlmostEqual(0.1, duration, places=1)
            else:
                # ironpython's time is weird
                self.assertTrue(0.0<duration<0.7)

    def testTimeoutConnect(self):
        # set up a unresponsive daemon
        with Pyro4.core.Daemon(port=0) as d:
            time.sleep(0.5)
            obj=MyThing()
            uri=d.register(obj)
            # we're not going to start the daemon's event loop
            p=Pyro4.core.Proxy(uri)
            p._pyroTimeout=0.2
            start=time.time()
            self.assertRaises(Pyro4.errors.TimeoutError, p.ping)
            duration=time.time()-start
            self.assertTrue(duration<2.0)
            
    def testProxySharing(self):
        class SharedProxyThread(threadutil.Thread):
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
                    print("Something went wrong in the thread (SharedProxyThread):")
                    print("".join(Pyro4.util.getPyroTraceback()))
        with Pyro4.core.Proxy(self.objectUri) as p:
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

    def testServerConnections(self):
        # check if the server allows to grow the number of connections
        proxies=[Pyro4.core.Proxy(self.objectUri) for _ in range(10)]
        try:
            for p in proxies:
                p._pyroTimeout=0.5
                p._pyroBind()
            for p in proxies:
                p.ping()
        finally:
            for p in proxies:
                p._pyroRelease()

    def testServerParallelism(self):
        class ClientThread(threadutil.Thread):
            def __init__(self, uri, name):
                super(ClientThread,self).__init__()
                self.setDaemon(True)
                self.proxy=Pyro4.core.Proxy(uri)
                self.name=name
                self.error=True
                self.proxy._pyroTimeout=5.0
                self.proxy._pyroBind()
            def run(self):
                try:
                    reply=self.proxy.delayAndId(0.5, self.name)
                    assert reply=="slept for "+self.name
                    self.error=False
                finally:
                    self.proxy._pyroRelease()
        threads=[]
        start=time.time()
        try:
            for i in range(6):
                t=ClientThread(self.objectUri,"t%d" % i)
                threads.append(t)
        except:
            # some exception (probably timeout) while creating clients
            # try to clean up some connections first
            for t in threads:
                t.proxy._pyroRelease()
            raise  # re-raise the exception
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            self.assertFalse(t.error, "all threads should report no errors")
        del threads
        duration=time.time()-start
        if Pyro4.config.SERVERTYPE=="multiplex":
            # multiplex based server doesn't execute calls in parallel,
            # so 6 threads times 0.5 seconds =~ 3 seconds
            self.assertTrue(2.5<duration<3.5)
        else:
            # thread based server does execute calls in parallel,
            # so 6 threads taking 0.5 seconds =~ 0.5 seconds passed
            self.assertTrue(0.4<duration<0.9)  # loose upper bound for slow jython

if os.name!="java":
    class ServerTestsMultiplexNoTimeout(ServerTestsThreadNoTimeout):
        SERVERTYPE="multiplex"
        COMMTIMEOUT=None
        def testProxySharing(self):
            pass
        def testException(self):
            pass

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
