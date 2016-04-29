"""
Tests for the daemon.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import sys
import time
import socket
import uuid
import unittest
import Pyro4.core
import Pyro4.naming
import Pyro4.constants
import Pyro4.socketutil
import Pyro4.message
from Pyro4.util import get_serializer_by_id
from Pyro4.errors import DaemonError, PyroError
from Pyro4 import current_context
from testsupport import *


class MyObj(object):
    def __init__(self, arg):
        self.arg = arg

    def __eq__(self, other):
        return self.arg == other.arg

    __hash__ = object.__hash__


class CustomDaemonInterface(Pyro4.core.DaemonObject):
    def __init__(self, daemon):
        super(CustomDaemonInterface, self).__init__(daemon)

    def custom_daemon_method(self):
        return 42


class ConnectionMock(object):
    def __init__(self, initial_msg=None):
        self.received = initial_msg.to_bytes() if initial_msg else b""

    def send(self, data):
        self.received += data

    def recv(self, datasize):
        chunk = self.received[:datasize]
        self.received = self.received[datasize:]
        return chunk


class DaemonTests(unittest.TestCase):
    # We create a daemon, but notice that we are not actually running the requestloop.
    # 'on-line' tests are all taking place in another test, to keep this one simple.

    def setUp(self):
        Pyro4.config.POLLTIMEOUT = 0.1

    def sendHandshakeMessage(self, conn, correlation_id=None):
        ser = get_serializer_by_id(Pyro4.message.SERIALIZER_MARSHAL)
        data, _ = ser.serializeData({"handshake": "hello", "object": Pyro4.constants.DAEMON_NAME}, False)
        annotations = {"CORR": correlation_id.bytes} if correlation_id else None
        msg = Pyro4.message.Message(Pyro4.message.MSG_CONNECT, data, Pyro4.message.SERIALIZER_MARSHAL, 0, 99, annotations=annotations)
        msg.send(conn)

    def testSerializerConfig(self):
        self.assertIsInstance(Pyro4.config.SERIALIZERS_ACCEPTED, set)
        self.assertIsInstance(Pyro4.config.SERIALIZER, basestring)
        self.assertGreater(len(Pyro4.config.SERIALIZERS_ACCEPTED), 1)

    def testSerializerAccepted(self):
        self.assertIn("marshal", Pyro4.config.SERIALIZERS_ACCEPTED)
        self.assertNotIn("pickle", Pyro4.config.SERIALIZERS_ACCEPTED)
        self.assertNotIn("dill", Pyro4.config.SERIALIZERS_ACCEPTED)
        with Pyro4.core.Daemon(port=0) as d:
            msg = Pyro4.message.Message(Pyro4.message.MSG_INVOKE, b"", Pyro4.message.SERIALIZER_MARSHAL, 0, 0, hmac_key=d._pyroHmacKey)
            cm = ConnectionMock(msg)
            d.handleRequest(cm)  # marshal serializer should be accepted
            msg = Pyro4.message.Message(Pyro4.message.MSG_INVOKE, b"", Pyro4.message.SERIALIZER_PICKLE, 0, 0, hmac_key=d._pyroHmacKey)
            cm = ConnectionMock(msg)
            try:
                d.handleRequest(cm)
                self.fail("should crash")
            except Pyro4.errors.ProtocolError as x:
                self.assertIn("serializer that is not accepted", str(x))
                pass
            import platform
            if platform.python_implementation() in ('PyPy', 'IronPython'):
                return
            msg = Pyro4.message.Message(Pyro4.message.MSG_INVOKE, b"", Pyro4.message.SERIALIZER_DILL, 0, 0, hmac_key=d._pyroHmacKey)
            cm = ConnectionMock(msg)
            try:
                d.handleRequest(cm)
                self.fail("should crash")
            except Pyro4.errors.ProtocolError as x:
                self.assertIn("serializer that is not accepted", str(x))
                pass

    def testDaemon(self):
        with Pyro4.core.Daemon(port=0) as d:
            hostname, port = d.locationStr.split(":")
            port = int(port)
            self.assertIn(Pyro4.constants.DAEMON_NAME, d.objectsById)
            self.assertEqual("PYRO:" + Pyro4.constants.DAEMON_NAME + "@" + d.locationStr, str(d.uriFor(Pyro4.constants.DAEMON_NAME)))
            # check the string representations
            expected = "<Pyro4.core.Daemon at 0x%x, %s, 1 objects>" % (id(d), d.locationStr)
            self.assertEqual(expected, str(d))
            self.assertEqual(expected, unicode(d))
            self.assertEqual(expected, repr(d))
            sockname = d.sock.getsockname()
            self.assertEqual(port, sockname[1])
            daemonobj = d.objectsById[Pyro4.constants.DAEMON_NAME]
            daemonobj.ping()
            daemonobj.registered()
            try:
                daemonobj.shutdown()
                self.fail("should not succeed to call unexposed method")
            except AttributeError:
                pass

    def testDaemonCustomInterface(self):
        with Pyro4.core.Daemon(port=0, interface=CustomDaemonInterface) as d:
            obj = d.objectsById[Pyro4.constants.DAEMON_NAME]
            self.assertEqual(42, obj.custom_daemon_method())

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "unix domain sockets required")
    def testDaemonUnixSocket(self):
        SOCKNAME = "test_unixsocket"
        with Pyro4.core.Daemon(unixsocket=SOCKNAME) as d:
            locationstr = "./u:" + SOCKNAME
            self.assertEqual(locationstr, d.locationStr)
            self.assertEqual("PYRO:" + Pyro4.constants.DAEMON_NAME + "@" + locationstr, str(d.uriFor(Pyro4.constants.DAEMON_NAME)))
            # check the string representations
            expected = "<Pyro4.core.Daemon at 0x%x, %s, 1 objects>" % (id(d), locationstr)
            self.assertEqual(expected, str(d))
            self.assertEqual(SOCKNAME, d.sock.getsockname())
            self.assertEqual(socket.AF_UNIX, d.sock.family)

    @unittest.skipUnless(hasattr(socket, "AF_UNIX") and sys.platform.startswith("linux"), "linux and unix domain sockets required")
    def testDaemonUnixSocketAbstractNS(self):
        SOCKNAME = "\0test_unixsocket"  # mind the \0 at the start
        with Pyro4.core.Daemon(unixsocket=SOCKNAME) as d:
            locationstr = "./u:" + SOCKNAME
            self.assertEqual(locationstr, d.locationStr)
            self.assertEqual("PYRO:" + Pyro4.constants.DAEMON_NAME + "@" + locationstr, str(d.uriFor(Pyro4.constants.DAEMON_NAME)))
            # check the string representations
            expected = "<Pyro4.core.Daemon at 0x%x, %s, 1 objects>" % (id(d), locationstr)
            self.assertEqual(expected, str(d))
            sn_bytes = tobytes(SOCKNAME)
            self.assertEqual(sn_bytes, d.sock.getsockname())
            self.assertEqual(socket.AF_UNIX, d.sock.family)

    def testServertypeThread(self):
        old_servertype = Pyro4.config.SERVERTYPE
        Pyro4.config.SERVERTYPE = "thread"
        with Pyro4.core.Daemon(port=0) as d:
            sock = d.sock
            self.assertIn(sock, d.sockets, "daemon's socketlist should contain the server socket")
            self.assertTrue(len(d.sockets) == 1, "daemon without connections should have just 1 socket")
        Pyro4.config.SERVERTYPE = old_servertype

    def testServertypeMultiplex(self):
        old_servertype = Pyro4.config.SERVERTYPE
        Pyro4.config.SERVERTYPE = "multiplex"
        with Pyro4.core.Daemon(port=0) as d:
            sock = d.sock
            self.assertIn(sock, d.sockets, "daemon's socketlist should contain the server socket")
            self.assertTrue(len(d.sockets) == 1, "daemon without connections should have just 1 socket")
        Pyro4.config.SERVERTYPE = old_servertype

    def testServertypeFoobar(self):
        old_servertype = Pyro4.config.SERVERTYPE
        Pyro4.config.SERVERTYPE = "foobar"
        self.assertRaises(PyroError, Pyro4.core.Daemon)
        Pyro4.config.SERVERTYPE = old_servertype

    def testRegisterTwice(self):
        with Pyro4.core.Daemon(port=0) as d:
            o1 = MyObj("object1")
            d.register(o1)
            with self.assertRaises(DaemonError) as x:
                d.register(o1)
            self.assertEqual("object already has a Pyro id", str(x.exception))
            d.unregister(o1)
            d.register(o1, "samename")
            o2 = MyObj("object2")
            with self.assertRaises(DaemonError) as x:
                d.register(o2, "samename")
            self.assertEqual("an object was already registered with that id", str(x.exception))
            self.assertTrue(hasattr(o1, "_pyroId"))
            self.assertTrue(hasattr(o1, "_pyroDaemon"))
            d.unregister(o1)
            self.assertFalse(hasattr(o1, "_pyroId"))
            self.assertFalse(hasattr(o1, "_pyroDaemon"))
            o1._pyroId = "FOOBAR"
            with self.assertRaises(DaemonError) as x:
                d.register(o1)
            self.assertEqual("object already has a Pyro id", str(x.exception))
            o1._pyroId = ""
            d.register(o1)  # with empty-string _pyroId register should work

    def testRegisterTwiceForced(self):
        with Pyro4.core.Daemon(port=0) as d:
            o1 = MyObj("object1")
            d.register(o1, "name1")
            d.register(o1, "name2", force=True)
            d.register(o1, "name1", force=True)
            self.assertIs(d.objectsById["name1"], d.objectsById["name2"])
            d.unregister(o1)
            o1._pyroId = "FOOBAR_ID"
            d.register(o1, "newname", force=True)
            self.assertEqual("newname", o1._pyroId)
            self.assertIn("newname", d.objectsById)

    def testRegisterEtc(self):
        d = Pyro4.core.Daemon(port=0)
        try:
            self.assertEqual(1, len(d.objectsById))
            o1 = MyObj("object1")
            o2 = MyObj("object2")
            d.register(o1)
            self.assertRaises(DaemonError, d.register, o2, Pyro4.constants.DAEMON_NAME)  # cannot use daemon name
            d.register(o2, "obj2a")

            self.assertEqual(3, len(d.objectsById))
            self.assertEqual(o1, d.objectsById[o1._pyroId])
            self.assertEqual(o2, d.objectsById["obj2a"])
            self.assertEqual("obj2a", o2._pyroId)
            self.assertEqual(d, o2._pyroDaemon)

            # test unregister
            d.unregister("unexisting_thingie")
            self.assertRaises(ValueError, d.unregister, None)
            d.unregister("obj2a")
            d.unregister(o1._pyroId)
            self.assertEqual(1, len(d.objectsById))
            self.assertNotIn(o1._pyroId, d.objectsById)
            self.assertNotIn(o2._pyroId, d.objectsById)

            # test unregister objects
            del o2._pyroId
            d.register(o2)
            objectid = o2._pyroId
            self.assertIn(objectid, d.objectsById)
            self.assertEqual(2, len(d.objectsById))
            d.unregister(o2)
            # no more _pyro attributes must remain after unregistering
            for attr in vars(o2):
                self.assertFalse(attr.startswith("_pyro"))
            self.assertEqual(1, len(d.objectsById))
            self.assertNotIn(objectid, d.objectsById)
            self.assertRaises(DaemonError, d.unregister, [1, 2, 3])

            # test unregister daemon name
            d.unregister(Pyro4.constants.DAEMON_NAME)
            self.assertIn(Pyro4.constants.DAEMON_NAME, d.objectsById)

            # weird args
            w = MyObj("weird")
            self.assertRaises(AttributeError, d.register, None)
            self.assertRaises(AttributeError, d.register, 4444)
            self.assertRaises(TypeError, d.register, w, 666)

            # uri return value from register
            uri = d.register(MyObj("xyz"))
            self.assertIsInstance(uri, Pyro4.core.URI)
            uri = d.register(MyObj("xyz"), "test.register")
            self.assertEqual("test.register", uri.object)

        finally:
            d.close()

    def testRegisterUnicode(self):
        with Pyro4.core.Daemon(port=0) as d:
            myobj1 = MyObj("hello1")
            myobj2 = MyObj("hello2")
            myobj3 = MyObj("hello3")
            uri1 = d.register(myobj1, "str_name")
            uri2 = d.register(myobj2, unicode("unicode_name"))
            uri3 = d.register(myobj3, "unicode_" + unichr(0x20ac))
            self.assertEqual(4, len(d.objectsById))
            uri = d.uriFor(myobj1)
            self.assertEqual(uri1, uri)
            _ = Pyro4.core.Proxy(uri)
            uri = d.uriFor(myobj2)
            self.assertEqual(uri2, uri)
            _ = Pyro4.core.Proxy(uri)
            uri = d.uriFor(myobj3)
            self.assertEqual(uri3, uri)
            _ = Pyro4.core.Proxy(uri)
            uri = d.uriFor("str_name")
            self.assertEqual(uri1, uri)
            _ = Pyro4.core.Proxy(uri)
            uri = d.uriFor(unicode("unicode_name"))
            self.assertEqual(uri2, uri)
            _ = Pyro4.core.Proxy(uri)
            uri = d.uriFor("unicode_" + unichr(0x20ac))
            self.assertEqual(uri3, uri)
            _ = Pyro4.core.Proxy(uri)

    def testDaemonObject(self):
        with Pyro4.core.Daemon(port=0) as d:
            daemon = Pyro4.core.DaemonObject(d)
            obj1 = MyObj("object1")
            obj2 = MyObj("object2")
            obj3 = MyObj("object2")
            d.register(obj1, "obj1")
            d.register(obj2, "obj2")
            d.register(obj3)
            daemon.ping()
            registered = daemon.registered()
            self.assertTrue(type(registered) is list)
            self.assertEqual(4, len(registered))
            self.assertIn("obj1", registered)
            self.assertIn("obj2", registered)
            self.assertIn(obj3._pyroId, registered)
            try:
                daemon.shutdown()
                self.fail("should not succeed to call unexposed method")
            except AttributeError:
                pass

    def testUriFor(self):
        d = Pyro4.core.Daemon(port=0)
        try:
            o1 = MyObj("object1")
            o2 = MyObj("object2")
            self.assertRaises(DaemonError, d.uriFor, o1)
            self.assertRaises(DaemonError, d.uriFor, o2)
            d.register(o1, None)
            d.register(o2, "object_two")
            o3 = MyObj("object3")
            self.assertRaises(DaemonError, d.uriFor, o3)  # can't get an uri for an unregistered object (note: unregistered name is ok)
            u1 = d.uriFor(o1)
            u2 = d.uriFor(o2._pyroId)
            u3 = d.uriFor("unexisting_thingie")  # unregistered name is no problem, it's just an uri we're requesting
            u4 = d.uriFor(o2)
            self.assertEqual(Pyro4.core.URI, type(u1))
            self.assertEqual("PYRO", u1.protocol)
            self.assertEqual("PYRO", u2.protocol)
            self.assertEqual("PYRO", u3.protocol)
            self.assertEqual("PYRO", u4.protocol)
            self.assertEqual("object_two", u4.object)
            self.assertEqual(Pyro4.core.URI("PYRO:unexisting_thingie@" + d.locationStr), u3)
        finally:
            d.close()

    def testDaemonWithStmt(self):
        d = Pyro4.core.Daemon()
        self.assertIsNotNone(d.transportServer)
        d.close()  # closes the transportserver and sets it to None
        self.assertIsNone(d.transportServer)
        with Pyro4.core.Daemon() as d:
            self.assertIsNotNone(d.transportServer)
            pass
        self.assertIsNone(d.transportServer)
        try:
            with Pyro4.core.Daemon() as d:
                print(1 // 0)  # cause an error
            self.fail("expected error")
        except ZeroDivisionError:
            pass
        self.assertIsNone(d.transportServer)
        d = Pyro4.core.Daemon()
        with d:
            pass
        try:
            with d:
                pass
            self.fail("expected error")
        except PyroError:
            # you cannot re-use a daemon object in multiple with statements
            pass
        d.close()

    def testRequestloopCondition(self):
        with Pyro4.core.Daemon(port=0) as d:
            condition = lambda: False
            start = time.time()
            d.requestLoop(loopCondition=condition)  # this should return almost immediately
            duration = time.time() - start
            self.assertAlmostEqual(0.0, duration, places=1)

    def testSimpleHandshake(self):
        conn = ConnectionMock()
        with Pyro4.core.Daemon(port=0) as d:
            self.sendHandshakeMessage(conn)
            success = d._handshake(conn)
            self.assertTrue(success)
            msg = Pyro4.message.Message.recv(conn, hmac_key=d._pyroHmacKey)
            self.assertEqual(Pyro4.message.MSG_CONNECTOK, msg.type)
            self.assertEqual(99, msg.seq)

    def testHandshakeDenied(self):
        class HandshakeFailDaemon(Pyro4.core.Daemon):
            def validateHandshake(self, conn, data):
                raise ValueError("handshake fail")
        conn = ConnectionMock()
        with HandshakeFailDaemon(port=0) as d:
            self.sendHandshakeMessage(conn)
            success = d._handshake(conn)
            self.assertFalse(success)
            msg = Pyro4.message.Message.recv(conn, hmac_key=d._pyroHmacKey)
            self.assertEqual(Pyro4.message.MSG_CONNECTFAIL, msg.type)
            self.assertEqual(99, msg.seq)
            self.assertTrue(b"handshake fail" in msg.data)

    def testCustomHandshake(self):
        conn = ConnectionMock()
        class CustomHandshakeDaemon(Pyro4.core.Daemon):
            def validateHandshake(self, conn, data):
                return ["sure", "have", "fun"]
            def annotations(self):
                ann = super(CustomHandshakeDaemon, self).annotations()
                ann["XYZZ"] = b"custom annotation set by daemon"
                return ann
        with CustomHandshakeDaemon(port=0) as d:
            corr_id = uuid.uuid4()
            self.sendHandshakeMessage(conn, correlation_id=corr_id)
            self.assertNotEqual(corr_id, current_context.correlation_id)
            success = d._handshake(conn)
            self.assertTrue(success)
            self.assertEqual(corr_id, current_context.correlation_id)
            msg = Pyro4.message.Message.recv(conn, hmac_key=d._pyroHmacKey)
            self.assertEqual(Pyro4.message.MSG_CONNECTOK, msg.type)
            self.assertEqual(99, msg.seq)
            self.assertEqual(2, len(msg.annotations))
            self.assertEqual(corr_id.bytes, msg.annotations["CORR"])
            self.assertEqual(b"custom annotation set by daemon", msg.annotations["XYZZ"])
            ser = get_serializer_by_id(msg.serializer_id)
            data = ser.deserializeData(msg.data, msg.flags & Pyro4.message.FLAGS_COMPRESSED)
            self.assertEqual(["sure", "have", "fun"], data)

    def testNAT(self):
        with Pyro4.core.Daemon() as d:
            self.assertIsNone(d.natLocationStr)
        with Pyro4.core.Daemon(nathost="nathosttest", natport=12345) as d:
            self.assertEqual("nathosttest:12345", d.natLocationStr)
            self.assertNotEqual(d.locationStr, d.natLocationStr)
            uri = d.register(MyObj(1))
            self.assertEqual("nathosttest:12345", uri.location)
            uri = d.uriFor("object")
            self.assertEqual("nathosttest:12345", uri.location)
            uri = d.uriFor("object", nat=False)
            self.assertNotEqual("nathosttest:12345", uri.location)
        try:
            _ = Pyro4.core.Daemon(nathost="bla")
            self.fail("expected error")
        except ValueError:
            pass
        try:
            _ = Pyro4.core.Daemon(natport=5555)
            self.fail("expected error")
        except ValueError:
            pass
        try:
            _ = Pyro4.core.Daemon(nathost="bla", natport=5555, unixsocket="testsock")
            self.fail("expected error")
        except ValueError:
            pass

    def testNATzeroPort(self):
        servertype = Pyro4.config.SERVERTYPE
        try:
            Pyro4.config.SERVERTYPE = "multiplex"
            with Pyro4.core.Daemon(nathost="nathosttest", natport=99999) as d:
                host, port = d.locationStr.split(":")
                self.assertNotEqual(99999, port)
                self.assertEqual("nathosttest:99999", d.natLocationStr)
            with Pyro4.core.Daemon(nathost="nathosttest", natport=0) as d:
                host, port = d.locationStr.split(":")
                self.assertEqual("nathosttest:%s" % port, d.natLocationStr)
            Pyro4.config.SERVERTYPE = "thread"
            with Pyro4.core.Daemon(nathost="nathosttest", natport=99999) as d:
                host, port = d.locationStr.split(":")
                self.assertNotEqual(99999, port)
                self.assertEqual("nathosttest:99999", d.natLocationStr)
            with Pyro4.core.Daemon(nathost="nathosttest", natport=0) as d:
                host, port = d.locationStr.split(":")
                self.assertEqual("nathosttest:%s" % port, d.natLocationStr)
        finally:
            Pyro4.config.SERVERTYPE = servertype

    def testNATconfig(self):
        try:
            Pyro4.config.NATHOST = None
            Pyro4.config.NATPORT = 0
            with Pyro4.core.Daemon() as d:
                self.assertIsNone(d.natLocationStr)
            Pyro4.config.NATHOST = "nathosttest"
            Pyro4.config.NATPORT = 12345
            with Pyro4.core.Daemon() as d:
                self.assertEqual("nathosttest:12345", d.natLocationStr)
        finally:
            Pyro4.config.NATHOST = None
            Pyro4.config.NATPORT = 0

    def testInstanceCreationSingle(self):
        def creator(clazz):
            return clazz("testname")
        @Pyro4.core.expose(instance_mode="single", instance_creator=creator)
        class TestClass:
            def __init__(self, name):
                self.name = name
        conn = Pyro4.socketutil.SocketConnection(socket.socket())
        d = Pyro4.core.Daemon()
        instance1 = d._getInstance(TestClass, conn)
        instance2 = d._getInstance(TestClass, conn)
        self.assertEqual("testname", instance1.name)
        self.assertIs(instance1, instance2)
        self.assertTrue(TestClass in d._pyroInstances)
        self.assertIs(instance1, d._pyroInstances[TestClass])
        self.assertFalse(TestClass in conn.pyroInstances)

    def testInstanceCreationSession(self):
        def creator(clazz):
            return clazz("testname")
        @Pyro4.core.expose(instance_mode="session", instance_creator=creator)
        class TestClass:
            def __init__(self, name):
                self.name = name
        conn1 = Pyro4.socketutil.SocketConnection(socket.socket())
        conn2 = Pyro4.socketutil.SocketConnection(socket.socket())
        d = Pyro4.core.Daemon()
        instance1a = d._getInstance(TestClass, conn1)
        instance1b = d._getInstance(TestClass, conn1)
        instance2a = d._getInstance(TestClass, conn2)
        instance2b = d._getInstance(TestClass, conn2)
        self.assertIs(instance1a, instance1b)
        self.assertIs(instance2a, instance2b)
        self.assertIsNot(instance1a, instance2a)
        self.assertFalse(TestClass in d._pyroInstances)
        self.assertTrue(TestClass in conn1.pyroInstances)
        self.assertTrue(TestClass in conn2.pyroInstances)
        self.assertIs(instance1a, conn1.pyroInstances[TestClass])
        self.assertIs(instance2a, conn2.pyroInstances[TestClass])

    def testInstanceCreationPerCall(self):
        def creator(clazz):
            return clazz("testname")
        @Pyro4.core.expose(instance_mode="percall", instance_creator=creator)
        class TestClass:
            def __init__(self, name):
                self.name = name
        conn = Pyro4.socketutil.SocketConnection(socket.socket())
        d = Pyro4.core.Daemon()
        instance1 = d._getInstance(TestClass, conn)
        instance2 = d._getInstance(TestClass, conn)
        self.assertIsNot(instance1, instance2)
        self.assertFalse(TestClass in d._pyroInstances)
        self.assertFalse(TestClass in conn.pyroInstances)

    def testInstanceCreationWrongType(self):
        def creator(clazz):
            return Pyro4.core.URI("PYRO:test@localhost:9999")
        @Pyro4.core.expose(instance_creator=creator)
        class TestClass:
            def method(self):
                pass
        conn = Pyro4.socketutil.SocketConnection(socket.socket())
        d = Pyro4.core.Daemon()
        with self.assertRaises(TypeError):
            d._getInstance(TestClass, conn)

    def testCombine(self):
        d1 = Pyro4.core.Daemon()
        d2 = Pyro4.core.Daemon()
        with self.assertRaises(TypeError):
            d1.combine(d2)
        d1.close()
        d2.close()
        try:
            Pyro4.config.SERVERTYPE = "multiplex"
            d1 = Pyro4.core.Daemon()
            d2 = Pyro4.core.Daemon()
            nsuri, nsd, bcd = Pyro4.naming.startNS(host="", bchost="")
            d1_selector = d1.transportServer.selector
            d1.combine(d2)
            d1.combine(nsd)
            d1.combine(bcd)
            self.assertIs(d1_selector, d1.transportServer.selector)
            self.assertIs(d1_selector, d2.transportServer.selector)
            self.assertIs(d1_selector, nsd.transportServer.selector)
            self.assertIs(d1_selector, bcd.transportServer.selector)
            self.assertEqual(4, len(d1.sockets))
            self.assertIn(d1.sock, d1.sockets)
            self.assertIn(d2.sock, d1.sockets)
            self.assertIn(nsd.sock, d1.sockets)
            self.assertIn(bcd, d1.sockets)
            bcd.close()
            nsd.close()
            d2.close()
            d1.close()
        finally:
            Pyro4.config.SERVERTYPE = "thread"


class MetaInfoTests(unittest.TestCase):
    def testMeta(self):
        with Pyro4.core.Daemon() as d:
            daemon_obj = d.objectsById[Pyro4.constants.DAEMON_NAME]
            self.assertTrue(len(daemon_obj.info()) > 10)
            meta = daemon_obj.get_metadata(Pyro4.constants.DAEMON_NAME)
            self.assertEqual(set(["get_metadata", "info", "ping", "registered"]), meta["methods"])

    def testMetaSerialization(self):
        with Pyro4.core.Daemon() as d:
            daemon_obj = d.objectsById[Pyro4.constants.DAEMON_NAME]
            meta = daemon_obj.get_metadata(Pyro4.constants.DAEMON_NAME)
            for ser_id in [Pyro4.message.SERIALIZER_JSON, Pyro4.message.SERIALIZER_MARSHAL, Pyro4.message.SERIALIZER_PICKLE, Pyro4.message.SERIALIZER_SERPENT, Pyro4.message.SERIALIZER_DILL]:
                import platform
                if platform.python_implementation() in ('IronPython', 'PyPy') and \
                   ser_id == Pyro4.message.SERIALIZER_DILL:
                    continue
                serializer = get_serializer_by_id(ser_id)
                data = serializer.dumps(meta)
                _ = serializer.loads(data)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
