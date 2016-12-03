"""
Tests for a running Pyro server, without timeouts.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import time
import sys
import uuid
import unittest
import Pyro4.core
import Pyro4.errors
import Pyro4.util
import Pyro4.message
from Pyro4 import threadutil, current_context
from testsupport import *


@Pyro4.expose
class ServerTestObject(object):
    something = 99
    dict_attr = {}

    def __init__(self):
        self._dictionary = {"number": 42}
        self.dict_attr = {"number2": 43}
        self._value = 12345

    def getDict(self):
        return self._dictionary

    def getDictAttr(self):
        return self.dict_attr

    def multiply(self, x, y):
        return x * y

    def divide(self, x, y):
        return x // y

    def ping(self):
        pass

    def echo(self, obj):
        return obj

    @Pyro4.oneway
    def oneway_delay(self, delay):
        time.sleep(delay)

    def delay(self, delay):
        time.sleep(delay)
        return "slept %d seconds" % delay

    def delayAndId(self, delay, id):
        time.sleep(delay)
        return "slept for " + str(id)

    def testargs(self, x, *args, **kwargs):
        return [x, list(args), kwargs]  # don't return tuples, this enables us to test json serialization as well.

    def nonserializableException(self):
        raise NonserializableError(("xantippe", lambda x: 0))

    @Pyro4.oneway
    def oneway_multiply(self, x, y):
        return x * y

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, newvalue):
        self._value = newvalue

    @property
    def dictionary(self):
        return self._dictionary

    def iterator(self):
        return iter(["one", "two", "three"])

    def generator(self):
        yield "one"
        yield "two"
        yield "three"


class NotEverythingExposedClass(object):
    def __init__(self, name):
        self.name = name

    @Pyro4.expose
    def getName(self):
        return self.name

    def unexposed(self):
        return "you should not see this"    # .... only when REQUIRE_EXPOSE is set to True is this valid


class DaemonLoopThread(threadutil.Thread):
    def __init__(self, pyrodaemon):
        super(DaemonLoopThread, self).__init__()
        self.setDaemon(True)
        self.pyrodaemon = pyrodaemon
        self.running = threadutil.Event()
        self.running.clear()

    def run(self):
        self.running.set()
        try:
            self.pyrodaemon.requestLoop()
        except Pyro4.errors.CommunicationError:
            pass  # ignore pyro communication errors


class DaemonWithSabotagedHandshake(Pyro4.core.Daemon):
    def _handshake(self, conn, denied_reason=None):
        # receive the client's handshake data
        msg = Pyro4.message.Message.recv(conn, [Pyro4.message.MSG_CONNECT], self._pyroHmacKey)
        # return a CONNECTFAIL always
        serializer = Pyro4.util.get_serializer_by_id(msg.serializer_id)
        data, _ = serializer.serializeData("rigged connection failure", compress=False)
        msg = Pyro4.message.Message(Pyro4.message.MSG_CONNECTFAIL, data, serializer.serializer_id, 0, 1, hmac_key=self._pyroHmacKey)
        conn.send(msg.to_bytes())
        return False


class ServerTestsBrokenHandshake(unittest.TestCase):
    def setUp(self):
        Pyro4.config.LOGWIRE = True
        Pyro4.config.SERIALIZERS_ACCEPTED.add("pickle")
        self.daemon = DaemonWithSabotagedHandshake(port=0)
        obj = ServerTestObject()
        uri = self.daemon.register(obj, "something")
        self.objectUri = uri
        self.daemonthread = DaemonLoopThread(self.daemon)
        self.daemonthread.start()
        self.daemonthread.running.wait()
        time.sleep(0.05)

    def tearDown(self):
        time.sleep(0.05)
        self.daemon.shutdown()
        self.daemonthread.join()
        Pyro4.config.SERIALIZERS_ACCEPTED.discard("pickle")

    def testDaemonConnectFail(self):
        # check what happens when the daemon responds with a failed connection msg
        with Pyro4.Proxy(self.objectUri) as p:
            try:
                p.ping()
                self.fail("expected CommunicationError")
            except Pyro4.errors.CommunicationError:
                xv = sys.exc_info()[1]
                message = str(xv)
                self.assertIn("reason:", message)
                self.assertIn("rigged connection failure", message)


class ServerTestsOnce(unittest.TestCase):
    """tests that are fine to run with just a single server type"""

    def setUp(self):
        Pyro4.config.LOGWIRE = True
        Pyro4.config.SERIALIZERS_ACCEPTED.add("pickle")
        self.daemon = Pyro4.core.Daemon(port=0)
        obj = ServerTestObject()
        uri = self.daemon.register(obj, "something")
        self.objectUri = uri
        obj2 = NotEverythingExposedClass("hello")
        self.daemon.register(obj2, "unexposed")
        self.daemonthread = DaemonLoopThread(self.daemon)
        self.daemonthread.start()
        self.daemonthread.running.wait()
        time.sleep(0.05)

    def tearDown(self):
        time.sleep(0.05)
        if self.daemon is not None:
            self.daemon.shutdown()
            self.daemonthread.join()
        Pyro4.config.SERIALIZERS_ACCEPTED.discard("pickle")

    def testPingMessage(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            p._pyroBind()
            conn = p._pyroConnection
            msg = Pyro4.message.Message(Pyro4.message.MSG_PING, b"something", 42, 0, 999, hmac_key=p._pyroHmacKey)
            conn.send(msg.to_bytes())
            msg = Pyro4.message.Message.recv(conn, [Pyro4.message.MSG_PING], hmac_key=p._pyroHmacKey)
            self.assertEqual(Pyro4.message.MSG_PING, msg.type)
            self.assertEqual(999, msg.seq)
            self.assertEqual(b"pong", msg.data)
            Pyro4.message.Message.ping(p._pyroConnection)  # the convenience method that does the above

    def testSequence(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            p.echo(1)
            p.echo(2)
            p.echo(3)
            self.assertEqual(3, p._pyroSeq, "should have 3 method calls")
            p._pyroSeq = 999   # hacking the seq nr won't have any effect because it is the reply from the server that is checked
            self.assertEqual(42, p.echo(42))

    def testMetaOffAttrs(self):
        try:
            old_meta = Pyro4.config.METADATA
            Pyro4.config.METADATA = False
            # should fail here, because there is no meta info about attributes
            with Pyro4.core.Proxy(self.objectUri) as p:
                self.assertEqual(55, p.multiply(5, 11))
                x = p.getDict()
                self.assertEqual({"number": 42}, x)
                # property
                with self.assertRaises(AttributeError):
                    p.dictionary.update({"more": 666})
                # attribute
                with self.assertRaises(AttributeError):
                    p.dict_attr.update({"more": 666})
                x = p.getDict()
                self.assertEqual({"number": 42}, x)
        finally:
            Pyro4.config.METADATA = old_meta

    def testMetaOnAttrs(self):
        try:
            old_meta = Pyro4.config.METADATA
            Pyro4.config.METADATA = True
            with Pyro4.core.Proxy(self.objectUri) as p:
                self.assertEqual(55, p.multiply(5, 11))
                # property
                x = p.getDict()
                self.assertEqual({"number": 42}, x)
                p.dictionary.update({"more": 666})  # should not fail because metadata is enabled and the dictionary property is retrieved as local copy
                x = p.getDict()
                self.assertEqual({"number": 42}, x)  # not updated remotely because we had a local copy
            with Pyro4.core.Proxy(self.objectUri) as p:
                with self.assertRaises(AttributeError):
                    # attribute should fail (meta only works for exposed properties)
                    p.dict_attr.update({"more": 666})
        finally:
            Pyro4.config.METADATA = old_meta

    def testSomeArgumentTypes(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            self.assertEqual([1, [], {}], p.testargs(1))
            self.assertEqual([1, [2, 3], {'a': 4}], p.testargs(1, 2, 3, a=4))
            self.assertEqual([1, [], {'a': 2}], p.testargs(1, **{'a': 2}))

    def testUnicodeKwargs(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            self.assertEqual([1, [], {unichr(65): 2}], p.testargs(1, **{unichr(65): 2}))
            result = p.testargs(unichr(0x20ac), **{unichr(0x20ac): 2})
            self.assertEqual(result[0], unichr(0x20ac))
            key = list(result[2].keys())[0]
            self.assertTrue(type(key) is unicode)
            self.assertEqual(key, unichr(0x20ac))

    def testNormalProxy(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            self.assertEqual(42, p.multiply(7, 6))

    def testExceptions(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            try:
                p.divide(1, 0)
                self.fail("should crash")
            except ZeroDivisionError:
                pass
            try:
                p.multiply("a", "b")
                self.fail("should crash")
            except TypeError:
                pass

    def testProxyMetadata(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            # unconnected proxies have empty metadata
            self.assertEqual(set(), p._pyroAttrs)
            self.assertEqual(set(), p._pyroMethods)
            self.assertEqual(set(), p._pyroOneway)
            # connecting it should obtain metadata (as long as METADATA is true)
            p._pyroBind()
            self.assertEqual({'value', 'dictionary'}, p._pyroAttrs)
            self.assertEqual({'echo', 'getDict', 'divide', 'nonserializableException', 'ping', 'oneway_delay', 'delayAndId', 'delay', 'testargs',
                                  'multiply', 'oneway_multiply', 'getDictAttr', 'iterator', 'generator'}, p._pyroMethods)
            self.assertEqual({'oneway_multiply', 'oneway_delay'}, p._pyroOneway)
            p._pyroAttrs = None
            p._pyroGetMetadata()
            self.assertEqual({'value', 'dictionary'}, p._pyroAttrs)
            p._pyroAttrs = None
            p._pyroGetMetadata(self.objectUri.object)
            self.assertEqual({'value', 'dictionary'}, p._pyroAttrs)
            p._pyroAttrs = None
            p._pyroGetMetadata(known_metadata={"attrs": set(), "oneway": set(), "methods": {"ping"}})
            self.assertEqual(set(), p._pyroAttrs)

    def testProxyAttrsMetadataOff(self):
        try:
            Pyro4.config.METADATA = False
            # read attributes
            with Pyro4.core.Proxy(self.objectUri) as p:
                a = p.multiply
                self.assertIsInstance(a, Pyro4.core._RemoteMethod)
                a = p.value
                self.assertIsInstance(a, Pyro4.core._RemoteMethod)
                a = p.non_existing_attribute
                self.assertIsInstance(a, Pyro4.core._RemoteMethod)
            # set attributes
            with Pyro4.core.Proxy(self.objectUri) as p:
                p.some_weird_attribute = 42
                self.assertEqual(42, p.some_weird_attribute)
        finally:
            Pyro4.config.METADATA = True

    def testProxyAttrsMetadataOn(self):
        try:
            Pyro4.config.METADATA = True
            # read attributes
            with Pyro4.core.Proxy(self.objectUri) as p:
                # unconnected proxy still has empty metadata.
                # but, as soon as an attribute is used, the metadata is obtained (as long as METADATA is true)
                a = p.value
                self.assertEqual(12345, a)
                a = p.multiply
                self.assertIsInstance(a, Pyro4.core._RemoteMethod)  # multiply is still a regular method
                with self.assertRaises(AttributeError):
                    _ = p.non_existing_attribute
            # set attributes, should also trigger getting metadata
            with Pyro4.core.Proxy(self.objectUri) as p:
                p.value = 42
                self.assertEqual(42, p.value)
                self.assertTrue("value" in p._pyroAttrs)
        finally:
            Pyro4.config.METADATA = True

    def testProxyAnnotations(self):
        class CustomAnnotationsProxy(Pyro4.core.Proxy):
            def __init__(self, uri, response):
                self.__dict__["response"] = response
                super(CustomAnnotationsProxy, self).__init__(uri)
            def _pyroAnnotations(self):
                ann = super(CustomAnnotationsProxy, self)._pyroAnnotations()
                ann["XYZZ"] = b"some data"
                self.__dict__["response"]["annotations_sent"] = ann
                return ann
            def _pyroResponseAnnotations(self, annotations, msgtype):
                self.__dict__["response"]["annotations"] = annotations
                self.__dict__["response"]["msgtype"] = msgtype
        response = {}
        corr_id = current_context.correlation_id = uuid.uuid4()
        with CustomAnnotationsProxy(self.objectUri, response) as p:
            p.ping()
        self.assertDictEqual({"CORR": corr_id.bytes, "XYZZ": b"some data"}, p.__dict__["response"]["annotations_sent"])
        self.assertEqual(Pyro4.message.MSG_RESULT, p.__dict__["response"]["msgtype"])
        self.assertDictEqual({"CORR": corr_id.bytes}, p.__dict__["response"]["annotations"])

    def testExposedNotRequired(self):
        try:
            old_require = Pyro4.config.REQUIRE_EXPOSE
            Pyro4.config.REQUIRE_EXPOSE = False
            with self.daemon.proxyFor("unexposed") as p:
                self.assertEqual({"unexposed", "getName"}, p._pyroMethods)
                self.assertEqual("hello", p.getName())
                self.assertEqual("you should not see this", p.unexposed())   # you *should* see it when REQUIRE_EXPOSE is False :)
        finally:
            Pyro4.config.REQUIRE_EXPOSE = old_require

    def testExposedRequired(self):
        try:
            old_require = Pyro4.config.REQUIRE_EXPOSE
            Pyro4.config.REQUIRE_EXPOSE = True
            with self.daemon.proxyFor("unexposed") as p:
                self.assertEqual({"getName"}, p._pyroMethods)
                self.assertEqual("hello", p.getName())
                with self.assertRaises(AttributeError) as e:
                    p.unexposed()
                expected_msg = "remote object '%s' has no exposed attribute or method 'unexposed'" % p._pyroUri
                self.assertEqual(expected_msg, str(e.exception))
                with self.assertRaises(AttributeError) as e:
                    p.unexposed_set = 999
                expected_msg = "remote object '%s' has no exposed attribute 'unexposed_set'" % p._pyroUri
                self.assertEqual(expected_msg, str(e.exception))
        finally:
            Pyro4.config.REQUIRE_EXPOSE = old_require

    def testProperties(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            _ = p.value
            # metadata should be loaded now
            self.assertEqual({"value", "dictionary"}, p._pyroAttrs)
            with self.assertRaises(AttributeError):
                _ = p.something
            with self.assertRaises(AttributeError):
                _ = p._dictionary
            with self.assertRaises(AttributeError):
                _ = p._value
            self.assertEqual(12345, p.value)
            self.assertEqual({"number": 42}, p.dictionary)

    def testHasAttr(self):
        try:
            Pyro4.config.METADATA = False
            with Pyro4.core.Proxy(self.objectUri) as p:
                # with metadata off, all attributes are considered valid (and return a RemoteMethod object)
                self.assertTrue(hasattr(p, "multiply"))
                self.assertTrue(hasattr(p, "oneway_multiply"))
                self.assertTrue(hasattr(p, "value"))
                self.assertTrue(hasattr(p, "_value"))
                self.assertTrue(hasattr(p, "_dictionary"))
                self.assertTrue(hasattr(p, "non_existing_attribute"))
            Pyro4.config.METADATA = True
            with Pyro4.core.Proxy(self.objectUri) as p:
                # with metadata on, hasattr actually gives proper results
                self.assertTrue(hasattr(p, "multiply"))
                self.assertTrue(hasattr(p, "oneway_multiply"))
                self.assertTrue(hasattr(p, "value"))
                self.assertFalse(hasattr(p, "_value"))
                self.assertFalse(hasattr(p, "_dictionary"))
                self.assertFalse(hasattr(p, "non_existing_attribute"))
        finally:
            Pyro4.config.METADATA = True

    def testProxyMetadataKnown(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            # unconnected proxies have empty metadata
            self.assertEqual(set(), p._pyroAttrs)
            self.assertEqual(set(), p._pyroMethods)
            self.assertEqual(set(), p._pyroOneway)
            # set some metadata manually, they should be overwritten at connection time
            p._pyroMethods = set("abc")
            p._pyroAttrs = set("xyz")
            p._pyroBind()
            self.assertNotEqual(set("xyz"), p._pyroAttrs)
            self.assertNotEqual(set("abc"), p._pyroMethods)
            self.assertNotEqual(set(), p._pyroOneway)

    def testNonserializableException_other(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            try:
                p.nonserializableException()
                self.fail("should crash")
            except Exception:
                xt, xv, tb = sys.exc_info()
                self.assertTrue(issubclass(xt, Pyro4.errors.PyroError))
                tblines = "\n".join(Pyro4.util.getPyroTraceback())
                self.assertTrue("unsupported serialized class" in tblines)

    def testNonserializableException_pickle(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            Pyro4.config.SERIALIZER = "pickle"
            try:
                p.nonserializableException()
                self.fail("should crash")
            except Exception:
                xt, xv, tb = sys.exc_info()
                self.assertTrue(issubclass(xt, Pyro4.errors.PyroError))
                tblines = "\n".join(Pyro4.util.getPyroTraceback())
                self.assertTrue("PyroError: Error serializing exception" in tblines)
                s1 = "Original exception: <class 'testsupport.NonserializableError'>:"
                s2 = "Original exception: <class 'PyroTests.testsupport.NonserializableError'>:"
                self.assertTrue(s1 in tblines or s2 in tblines)
                self.assertTrue("raise NonserializableError((\"xantippe" in tblines)
            finally:
                Pyro4.config.SERIALIZER = "serpent"

    def testBatchProxy(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            batch = Pyro4.batch(p)
            self.assertIsNone(batch.multiply(7, 6))
            self.assertIsNone(batch.divide(999, 3))
            self.assertIsNone(batch.ping())
            self.assertIsNone(batch.divide(999, 0))  # force an exception here
            self.assertIsNone(batch.multiply(3, 4))  # this call should not be performed after the error
            results = batch()
            self.assertEqual(42, next(results))
            self.assertEqual(333, next(results))
            self.assertIsNone(next(results))
            self.assertRaises(ZeroDivisionError, next, results)  # 999//0 should raise this error
            self.assertRaises(StopIteration, next, results)  # no more results should be available after the error

    def testAsyncProxy(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            async = Pyro4.async(p)
            async._pyroBind()  # force that any metadata is processed
            begin = time.time()
            result = async.delayAndId(1, 42)
            duration = time.time() - begin
            self.assertTrue(duration < 0.1)
            self.assertFalse(result.ready)
            self.assertFalse(result.wait(0.5))  # not available within 0.5 sec
            self.assertEqual("slept for 42", result.value)
            self.assertTrue(result.ready)
            self.assertTrue(result.wait())

    def testAsyncProxyCallchain(self):
        class FuncHolder(object):
            count = threadutil.AtomicCounter()

            def function(self, value, increase=1):
                self.count.incr()
                return value + increase

        with Pyro4.core.Proxy(self.objectUri) as p:
            async = Pyro4.async(p)
            async._pyroBind()  # force that any metadata is processed
            holder = FuncHolder()
            begin = time.time()
            result = async.multiply(2, 3)
            result.then(holder.function, increase=10) \
                .then(holder.function, increase=5) \
                .then(holder.function)
            duration = time.time() - begin
            self.assertTrue(duration < 0.1)
            value = result.value
            self.assertTrue(result.ready)
            self.assertEqual(22, value)
            self.assertEqual(3, holder.count.value)

    def testBatchOneway(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            batch = Pyro4.batch(p)
            self.assertIsNone(batch.multiply(7, 6))
            self.assertIsNone(batch.delay(1))  # a delay shouldn't matter with oneway
            self.assertIsNone(batch.multiply(3, 4))
            begin = time.time()
            results = batch(oneway=True)
            duration = time.time() - begin
            self.assertTrue(duration < 0.1, "oneway batch with delay should return almost immediately")
            self.assertIsNone(results)

    def testBatchAsync(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            batch = Pyro4.batch(p)
            self.assertIsNone(batch.multiply(7, 6))
            self.assertIsNone(batch.delay(1))  # a delay shouldn't matter with async
            self.assertIsNone(batch.multiply(3, 4))
            begin = time.time()
            asyncresult = batch(async=True)
            duration = time.time() - begin
            self.assertTrue(duration < 0.1, "async batch with delay should return almost immediately")
            results = asyncresult.value
            self.assertEqual(42, next(results))
            self.assertEqual("slept 1 seconds", next(results))
            self.assertEqual(12, next(results))
            self.assertRaises(StopIteration, next, results)  # no more results should be available

    def testBatchAsyncCallchain(self):
        class FuncHolder(object):
            count = threadutil.AtomicCounter()

            def function(self, values):
                result = [value + 1 for value in values]
                self.count.incr()
                return result

        with Pyro4.core.Proxy(self.objectUri) as p:
            batch = Pyro4.batch(p)
            self.assertIsNone(batch.multiply(7, 6))
            self.assertIsNone(batch.multiply(3, 4))
            result = batch(async=True)
            holder = FuncHolder()
            result.then(holder.function).then(holder.function)
            value = result.value
            self.assertTrue(result.ready)
            self.assertEqual([44, 14], value)
            self.assertEqual(2, holder.count.value)

    def testPyroTracebackNormal(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            try:
                p.divide(999, 0)  # force error here
                self.fail("expected error")
            except ZeroDivisionError:
                # going to check if the magic pyro traceback attribute is available for batch methods too
                tb = "".join(Pyro4.util.getPyroTraceback())
                self.assertIn("Remote traceback:", tb)  # validate if remote tb is present
                self.assertIn("ZeroDivisionError", tb)  # the error
                self.assertIn("return x // y", tb)  # the statement

    def testPyroTracebackBatch(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            batch = Pyro4.batch(p)
            self.assertIsNone(batch.divide(999, 0))  # force an exception here
            results = batch()
            try:
                next(results)
                self.fail("expected error")
            except ZeroDivisionError:
                # going to check if the magic pyro traceback attribute is available for batch methods too
                tb = "".join(Pyro4.util.getPyroTraceback())
                self.assertIn("Remote traceback:", tb)  # validate if remote tb is present
                self.assertIn("ZeroDivisionError", tb)  # the error
                self.assertIn("return x // y", tb)  # the statement
            self.assertRaises(StopIteration, next, results)  # no more results should be available after the error

    def testAutoProxy(self):
        obj = ServerTestObject()
        Pyro4.config.SERIALIZER = "pickle"
        try:
            with Pyro4.core.Proxy(self.objectUri) as p:
                Pyro4.config.AUTOPROXY = False  # make sure autoproxy is disabled
                result = p.echo(obj)
                self.assertIsInstance(result, ServerTestObject)
                self.daemon.register(obj)
                result = p.echo(obj)
                self.assertIsInstance(result, ServerTestObject, "with autoproxy off the object should be an instance of the class")
                self.daemon.unregister(obj)
                result = p.echo(obj)
                self.assertIsInstance(result, ServerTestObject, "serialized object must still be normal object")
                Pyro4.config.AUTOPROXY = True  # make sure autoproxying is enabled
                result = p.echo(obj)
                self.assertIsInstance(result, ServerTestObject, "non-pyro object must be returned as normal class")
                self.daemon.register(obj)
                result = p.echo(obj)
                self.assertIsInstance(result, Pyro4.core.Proxy, "serialized pyro object must be a proxy")
                self.daemon.unregister(obj)
                result = p.echo(obj)
                self.assertIsInstance(result, ServerTestObject, "unregistered pyro object must be normal class again")
                # note: the custom serializer may still be active but it should be smart enough to see
                # that the object is no longer a pyro object, and therefore, no proxy should be created.
        finally:
            Pyro4.config.AUTOPROXY = True
            Pyro4.config.SERIALIZER = "serpent"

    def testConnectOnce(self):
        with Pyro4.core.Proxy(self.objectUri) as proxy:
            self.assertTrue(proxy._pyroBind(), "first bind should always connect")
            self.assertFalse(proxy._pyroBind(), "second bind should not connect again")

    def testConnectingThreads(self):
        class ConnectingThread(threadutil.Thread):
            new_connections = threadutil.AtomicCounter()

            def __init__(self, proxy, event):
                threadutil.Thread.__init__(self)
                self.proxy = proxy
                self.event = event
                self.setDaemon(True)
                self.new_connections.reset()

            def run(self):
                self.event.wait()
                if self.proxy._pyroBind():
                    ConnectingThread.new_connections.incr()  # 1 more new connection done

        with Pyro4.core.Proxy(self.objectUri) as proxy:
            event = threadutil.Event()
            threads = [ConnectingThread(proxy, event) for _ in range(20)]
            for t in threads:
                t.start()
            event.set()
            for t in threads:
                t.join()
            self.assertEqual(1, ConnectingThread.new_connections.value)  # proxy shared among threads must still have only 1 connect done

    def testMaxMsgSize(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            bigobject = [42] * 1000
            result = p.echo(bigobject)
            self.assertEqual(result, bigobject)
            Pyro4.config.MAX_MESSAGE_SIZE = 999
            try:
                _ = p.echo(bigobject)
                self.fail("should fail with ProtocolError msg too large")
            except Pyro4.errors.ProtocolError:
                pass
            Pyro4.config.MAX_MESSAGE_SIZE = 0

    def testIterator(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            iterator = p.iterator()
            self.assertIsInstance(iterator, Pyro4.core._StreamResultIterator)
            self.assertEqual("one", next(iterator))
            self.assertEqual("two", next(iterator))
            self.assertEqual("three", next(iterator))
            with self.assertRaises(StopIteration):
                next(iterator)
            iterator.close()

    def testGenerator(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            generator = p.generator()
            self.assertIsInstance(generator, Pyro4.core._StreamResultIterator)
            self.assertEqual("one", next(generator))
            self.assertEqual("two", next(generator))
            self.assertEqual("three", next(generator))
            with self.assertRaises(StopIteration):
                next(generator)
            generator.close()

    def testCleanup(self):
        p1 = Pyro4.core.Proxy(self.objectUri)
        p2 = Pyro4.core.Proxy(self.objectUri)
        p3 = Pyro4.core.Proxy(self.objectUri)
        p1.echo(42)
        p2.echo(42)
        p3.echo(42)
        # we have several active connections still up, see if we can cleanly shutdown the daemon
        # (it should interrupt the worker's socket connections)
        time.sleep(0.1)
        self.daemon.shutdown()
        self.daemon = None
        p1._pyroRelease()
        p2._pyroRelease()
        p3._pyroRelease()


class ServerTestsThreadNoTimeout(unittest.TestCase):
    SERVERTYPE = "thread"
    COMMTIMEOUT = None

    def setUp(self):
        Pyro4.config.LOGWIRE = True
        Pyro4.config.POLLTIMEOUT = 0.1
        Pyro4.config.SERVERTYPE = self.SERVERTYPE
        Pyro4.config.COMMTIMEOUT = self.COMMTIMEOUT
        Pyro4.config.SERIALIZERS_ACCEPTED.add("pickle")
        self.daemon = Pyro4.core.Daemon(port=0)
        obj = ServerTestObject()
        uri = self.daemon.register(obj, "something")
        self.objectUri = uri
        self.daemonthread = DaemonLoopThread(self.daemon)
        self.daemonthread.start()
        self.daemonthread.running.wait()
        time.sleep(0.05)

    def tearDown(self):
        time.sleep(0.05)
        self.daemon.shutdown()
        self.daemonthread.join()
        Pyro4.config.SERVERTYPE = "thread"
        Pyro4.config.COMMTIMEOUT = None
        Pyro4.config.SERIALIZERS_ACCEPTED.discard("pickle")

    def testConnectionStuff(self):
        p1 = Pyro4.core.Proxy(self.objectUri)
        p2 = Pyro4.core.Proxy(self.objectUri)
        self.assertIsNone(p1._pyroConnection)
        self.assertIsNone(p2._pyroConnection)
        p1.ping()
        p2.ping()
        _ = p1.multiply(11, 5)
        _ = p2.multiply(11, 5)
        self.assertIsNotNone(p1._pyroConnection)
        self.assertIsNotNone(p2._pyroConnection)
        p1._pyroRelease()
        p1._pyroRelease()
        p2._pyroRelease()
        p2._pyroRelease()
        self.assertIsNone(p1._pyroConnection)
        self.assertIsNone(p2._pyroConnection)
        p1._pyroBind()
        _ = p1.multiply(11, 5)
        _ = p2.multiply(11, 5)
        self.assertIsNotNone(p1._pyroConnection)
        self.assertIsNotNone(p2._pyroConnection)
        self.assertEqual("PYRO", p1._pyroUri.protocol)
        self.assertEqual("PYRO", p2._pyroUri.protocol)
        p1._pyroRelease()
        p2._pyroRelease()

    def testReconnectAndCompression(self):
        # try reconnects
        with Pyro4.core.Proxy(self.objectUri) as p:
            self.assertIsNone(p._pyroConnection)
            p._pyroReconnect(tries=100)
            self.assertIsNotNone(p._pyroConnection)
        self.assertIsNone(p._pyroConnection)
        # test compression:
        try:
            with Pyro4.core.Proxy(self.objectUri) as p:
                Pyro4.config.COMPRESSION = True
                self.assertEqual(55, p.multiply(5, 11))
                self.assertEqual("*" * 1000, p.multiply("*" * 500, 2))
        finally:
            Pyro4.config.COMPRESSION = False

    def testOnewayMetaOn(self):
        Pyro4.config.METADATA = True
        with Pyro4.core.Proxy(self.objectUri) as p:
            self.assertEqual(set(), p._pyroOneway)  # when not bound, no meta info exchange has been done
            p._pyroBind()
            self.assertIn("oneway_multiply", p._pyroOneway)  # after binding, meta info has been processed
            self.assertEqual(55, p.multiply(5, 11))  # not tagged as @Pyro4.oneway
            self.assertIsNone(p.oneway_multiply(5, 11))  # tagged as @Pyro4.oneway
            p._pyroOneway = set()
            self.assertEqual(55, p.multiply(5, 11))
            self.assertEqual(55, p.oneway_multiply(5, 11))
            # check nonexisting method behavoir for oneway methods
            with self.assertRaises(AttributeError):
                p.nonexisting_method()
            p._pyroOneway.add("nonexisting_method")
            # now it should still fail because of metadata telling Pyro what methods actually exist
            with self.assertRaises(AttributeError):
                p.nonexisting_method()

    def testOnewayMetaOff(self):
        Pyro4.config.METADATA = False
        with Pyro4.core.Proxy(self.objectUri) as p:
            self.assertEqual(set(), p._pyroOneway)  # when not bound, no meta info exchange has been done
            p._pyroBind()
            self.assertEqual(set(), p._pyroOneway)  # after binding, no meta info exchange has been done because disabled
            self.assertEqual(55, p.multiply(5, 11))
            self.assertEqual(55, p.oneway_multiply(5, 11))
            # check nonexisting method behavoir for oneway methods
            with self.assertRaises(AttributeError):
                p.nonexisting_method()
            p._pyroOneway.add("nonexisting_method")
            # now it shouldn't fail because of oneway semantics (!) (and becaue there's no metadata to tell Pyro that the method doesn't exist)
            p.nonexisting_method()
        Pyro4.config.METADATA = True

    def testOnewayWithProxySubclass(self):
        Pyro4.config.METADATA = False

        class ProxyWithOneway(Pyro4.core.Proxy):
            def __init__(self, arg):
                super(ProxyWithOneway, self).__init__(arg)
                self._pyroOneway = {"oneway_multiply", "multiply"}

        with ProxyWithOneway(self.objectUri) as p:
            self.assertIsNone(p.oneway_multiply(5, 11))
            self.assertIsNone(p.multiply(5, 11))
            p._pyroOneway = set()
            self.assertEqual(55, p.oneway_multiply(5, 11))
            self.assertEqual(55, p.multiply(5, 11))
        Pyro4.config.METADATA = True

    def testOnewayDelayed(self):
        try:
            with Pyro4.core.Proxy(self.objectUri) as p:
                p.ping()
                Pyro4.config.ONEWAY_THREADED = True  # the default
                now = time.time()
                p.oneway_delay(1)  # oneway so we should continue right away
                time.sleep(0.01)
                self.assertTrue(time.time() - now < 0.2, "delay should be running as oneway")
                now = time.time()
                self.assertEqual(55, p.multiply(5, 11), "expected a normal result from a non-oneway call")
                self.assertTrue(time.time() - now < 0.2, "delay should be running in its own thread")
                # make oneway calls run in the server thread
                # we can change the config here and the server will pick it up on the fly
                Pyro4.config.ONEWAY_THREADED = False
                now = time.time()
                p.oneway_delay(1)  # oneway so we should continue right away
                time.sleep(0.01)
                self.assertTrue(time.time() - now < 0.2, "delay should be running as oneway")
                now = time.time()
                self.assertEqual(55, p.multiply(5, 11), "expected a normal result from a non-oneway call")
                self.assertFalse(time.time() - now < 0.2, "delay should be running in the server thread")
        finally:
            Pyro4.config.ONEWAY_THREADED = True  # back to normal

    def testSerializeConnected(self):
        # online serialization tests
        ser = Pyro4.util.get_serializer(Pyro4.config.SERIALIZER)
        proxy = Pyro4.core.Proxy(self.objectUri)
        proxy._pyroBind()
        self.assertIsNotNone(proxy._pyroConnection)
        p, _ = ser.serializeData(proxy)
        proxy2 = ser.deserializeData(p)
        self.assertIsNone(proxy2._pyroConnection)
        self.assertIsNotNone(proxy._pyroConnection)
        self.assertEqual(proxy2._pyroUri, proxy._pyroUri)
        proxy2._pyroBind()
        self.assertIsNotNone(proxy2._pyroConnection)
        self.assertIsNot(proxy2._pyroConnection, proxy._pyroConnection)
        proxy._pyroRelease()
        proxy2._pyroRelease()
        self.assertIsNone(proxy._pyroConnection)
        self.assertIsNone(proxy2._pyroConnection)
        proxy.ping()
        proxy2.ping()
        # try copying a connected proxy
        import copy
        proxy3 = copy.copy(proxy)
        self.assertIsNone(proxy3._pyroConnection)
        self.assertIsNotNone(proxy._pyroConnection)
        self.assertEqual(proxy3._pyroUri, proxy._pyroUri)
        self.assertIsNot(proxy3._pyroUri, proxy._pyroUri)
        proxy._pyroRelease()
        proxy2._pyroRelease()
        proxy3._pyroRelease()

    def testException(self):
        with Pyro4.core.Proxy(self.objectUri) as p:
            try:
                p.divide(1, 0)
            except:
                et, ev, tb = sys.exc_info()
                self.assertEqual(ZeroDivisionError, et)
                pyrotb = "".join(Pyro4.util.getPyroTraceback(et, ev, tb))
                self.assertIn("Remote traceback", pyrotb)
                self.assertIn("ZeroDivisionError", pyrotb)
                del tb

    def testTimeoutCall(self):
        Pyro4.config.COMMTIMEOUT = None
        with Pyro4.core.Proxy(self.objectUri) as p:
            p.ping()
            start = time.time()
            p.delay(0.5)
            duration = time.time() - start
            self.assertTrue(0.4 < duration < 0.6)
            p._pyroTimeout = 0.1
            start = time.time()
            self.assertRaises(Pyro4.errors.TimeoutError, p.delay, 1)
            duration = time.time() - start
            if sys.platform != "cli":
                self.assertLess(duration, 0.3)
            else:
                # ironpython's time is weird
                self.assertTrue(0.0 < duration < 0.7)

    def testTimeoutConnect(self):
        # set up a unresponsive daemon
        with Pyro4.core.Daemon(port=0) as d:
            time.sleep(0.5)
            obj = ServerTestObject()
            uri = d.register(obj)
            # we're not going to start the daemon's event loop
            p = Pyro4.core.Proxy(uri)
            p._pyroTimeout = 0.2
            start = time.time()
            with self.assertRaises(Pyro4.errors.TimeoutError) as e:
                p.ping()
            self.assertEqual("receiving: timeout", str(e.exception))

    def testProxySharing(self):
        class SharedProxyThread(threadutil.Thread):
            def __init__(self, proxy):
                super(SharedProxyThread, self).__init__()
                self.proxy = proxy
                self.terminate = False
                self.error = True
                self.setDaemon(True)

            def run(self):
                try:
                    while not self.terminate:
                        reply = self.proxy.multiply(5, 11)
                        assert reply == 55
                        time.sleep(0.001)
                    self.error = False
                except:
                    print("Something went wrong in the thread (SharedProxyThread):")
                    print("".join(Pyro4.util.getPyroTraceback()))

        with Pyro4.core.Proxy(self.objectUri) as p:
            threads = []
            for i in range(5):
                t = SharedProxyThread(p)
                threads.append(t)
                t.start()
            time.sleep(1)
            for t in threads:
                t.terminate = True
                t.join()
            for t in threads:
                self.assertFalse(t.error, "all threads should report no errors")

    def testServerConnections(self):
        # check if the server allows to grow the number of connections
        proxies = [Pyro4.core.Proxy(self.objectUri) for _ in range(10)]
        try:
            for p in proxies:
                p._pyroTimeout = 0.5
                p._pyroBind()
            for p in proxies:
                p.ping()
        finally:
            for p in proxies:
                p._pyroRelease()

    def testServerParallelism(self):
        class ClientThread(threadutil.Thread):
            def __init__(self, uri, name):
                super(ClientThread, self).__init__()
                self.setDaemon(True)
                self.proxy = Pyro4.core.Proxy(uri)
                self.name = name
                self.error = True
                self.proxy._pyroTimeout = 5.0
                self.proxy._pyroBind()

            def run(self):
                try:
                    reply = self.proxy.delayAndId(0.5, self.name)
                    assert reply == "slept for " + self.name
                    self.error = False
                finally:
                    self.proxy._pyroRelease()

        threads = []
        start = time.time()
        try:
            for i in range(6):
                t = ClientThread(self.objectUri, "t%d" % i)
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
        duration = time.time() - start
        if Pyro4.config.SERVERTYPE == "multiplex":
            # multiplex based server doesn't execute calls in parallel,
            # so 6 threads times 0.5 seconds =~ 3 seconds
            self.assertTrue(2.5 < duration < 3.5)
        else:
            # thread based server does execute calls in parallel,
            # so 6 threads taking 0.5 seconds =~ 0.5 seconds passed
            self.assertTrue(0.4 < duration < 0.9)

    def testGeneratorProxyClose(self):
        p = Pyro4.core.Proxy(self.objectUri)
        generator = p.generator()
        p._pyroRelease()
        with self.assertRaises(Pyro4.errors.ConnectionClosedError):
            next(generator)

    def testGeneratorLinger(self):
        orig_linger = Pyro4.config.ITER_STREAM_LINGER
        orig_commt = Pyro4.config.COMMTIMEOUT
        orig_pollt = Pyro4.config.POLLTIMEOUT
        try:
            Pyro4.config.ITER_STREAM_LINGER = 0.5
            Pyro4.config.COMMTIMEOUT = 0.2
            Pyro4.config.POLLTIMEOUT = 0.2
            p = Pyro4.core.Proxy(self.objectUri)
            generator = p.generator()
            self.assertEqual("one", next(generator))
            p._pyroRelease()
            with self.assertRaises(Pyro4.errors.ConnectionClosedError):
                next(generator)
            p._pyroReconnect()
            self.assertEqual("two", next(generator), "generator should resume after reconnect")
            # check that after the linger time passes, the generator *is* gone
            p._pyroRelease()
            time.sleep(2)
            p._pyroReconnect()
            with self.assertRaises(Pyro4.errors.PyroError):  # should not be resumable anymore
                next(generator)
        finally:
            Pyro4.config.ITER_STREAM_LINGER = orig_linger
            Pyro4.config.COMMTIMEOUT = orig_commt
            Pyro4.config.POLLTIMEOUT = orig_pollt

    def testGeneratorNoLinger(self):
        orig_linger = Pyro4.config.ITER_STREAM_LINGER
        try:
            p = Pyro4.core.Proxy(self.objectUri)
            Pyro4.config.ITER_STREAM_LINGER = 0  # disable linger
            generator = p.generator()
            self.assertEqual("one", next(generator))
            p._pyroRelease()
            with self.assertRaises(Pyro4.errors.ConnectionClosedError):
                next(generator)
            p._pyroReconnect()
            with self.assertRaises(Pyro4.errors.PyroError):  # should not be resumable after reconnect
                next(generator)
            generator.close()
        finally:
            Pyro4.config.ITER_STREAM_LINGER = orig_linger


class ServerTestsMultiplexNoTimeout(ServerTestsThreadNoTimeout):
    SERVERTYPE = "multiplex"
    COMMTIMEOUT = None

    def testProxySharing(self):
        pass

    def testException(self):
        pass


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
