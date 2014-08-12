"""
Tests for the core logic.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import copy
import logging
import os
import sys
import time
import warnings
import Pyro4.configuration
import Pyro4.core

import Pyro4.errors
import Pyro4.constants
import Pyro4.futures
from testsupport import *


if (3, 0) <= sys.version_info < (3, 4):
    import imp
    reload = imp.reload
elif sys.version_info >= (3, 4):
    import importlib
    reload = importlib.reload


class CoreTestsWithoutHmac(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore")
        Pyro4.config.reset()

    def testProxy(self):
        Pyro4.config.HMAC_KEY = None
        # check that proxy without hmac is possible
        _ = Pyro4.Proxy("PYRO:object@host:9999")

    def testDaemon(self):
        Pyro4.config.HMAC_KEY = None
        # check that daemon without hmac is possible
        d = Pyro4.Daemon()
        d.shutdown()

    @unittest.skipIf(sys.version_info < (3, 0), "hmac bytes only checked on python 3.0+")
    def testHmacBytes(self):
        Pyro4.config.HMAC_KEY = "stringnotallowed"
        with self.assertRaises(Pyro4.errors.PyroError):
            Pyro4.core._check_hmac()
        Pyro4.config.HMAC_KEY = None


class CoreTests(unittest.TestCase):
    def setUp(self):
        Pyro4.config.HMAC_KEY = b"testsuite"

    def tearDown(self):
        Pyro4.config.HMAC_KEY = None

    def testConfig(self):
        self.assertTrue(type(Pyro4.config.COMPRESSION) is bool)
        self.assertTrue(type(Pyro4.config.NS_PORT) is int)
        config = Pyro4.config.asDict()
        self.assertTrue(type(config) is dict)
        self.assertIn("COMPRESSION", config)
        self.assertEqual(Pyro4.config.COMPRESSION, config["COMPRESSION"])

    def testConfigValid(self):
        try:
            Pyro4.config.XYZ_FOOBAR = True  # don't want to allow weird config names
            self.fail("expected exception for weird config item")
        except AttributeError:
            pass

    def testConfigParseBool(self):
        config = Pyro4.configuration.Configuration()
        self.assertTrue(type(config.COMPRESSION) is bool)
        os.environ["PYRO_COMPRESSION"] = "yes"
        config.reset()
        self.assertTrue(config.COMPRESSION)
        os.environ["PYRO_COMPRESSION"] = "off"
        config.reset()
        self.assertFalse(config.COMPRESSION)
        os.environ["PYRO_COMPRESSION"] = "foobar"
        self.assertRaises(ValueError, config.reset)
        del os.environ["PYRO_COMPRESSION"]
        config.reset()

    def testConfigDump(self):
        config = Pyro4.configuration.Configuration()
        dump = config.dump()
        self.assertIn("version:", dump)
        self.assertIn("LOGLEVEL", dump)

    def testLogInit(self):
        _ = logging.getLogger("Pyro4")
        os.environ["PYRO_LOGLEVEL"] = "DEBUG"
        os.environ["PYRO_LOGFILE"] = "{stderr}"
        reload(Pyro4)
        _ = logging.getLogger("Pyro4")
        os.environ["PYRO_LOGFILE"] = "Pyro.log"
        reload(Pyro4)
        _ = logging.getLogger("Pyro4")
        del os.environ["PYRO_LOGLEVEL"]
        del os.environ["PYRO_LOGFILE"]
        reload(Pyro4)
        _ = logging.getLogger("Pyro4")

    def testUriStrAndRepr(self):
        uri = "PYRONAME:some_obj_name"
        p = Pyro4.core.URI(uri)
        self.assertEqual(uri, str(p))
        uri = "PYRONAME:some_obj_name@host.com"
        p = Pyro4.core.URI(uri)
        self.assertEqual(uri + ":" + str(Pyro4.config.NS_PORT), str(p))  # a PYRONAME uri with a hostname gets a port too if omitted
        uri = "PYRONAME:some_obj_name@host.com:8888"
        p = Pyro4.core.URI(uri)
        self.assertEqual(uri, str(p))
        expected = "<Pyro4.core.URI at 0x%x, PYRONAME:some_obj_name@host.com:8888>" % id(p)
        self.assertEqual(expected, repr(p))
        uri = "PYRO:12345@host.com:9999"
        p = Pyro4.core.URI(uri)
        self.assertEqual(uri, str(p))
        self.assertEqual(uri, p.asString())
        uri = "PYRO:12345@./u:sockname"
        p = Pyro4.core.URI(uri)
        self.assertEqual(uri, str(p))
        uri = "PYRO:12345@./u:sockname"
        unicodeuri = unicode(uri)
        p = Pyro4.core.URI(unicodeuri)
        self.assertEqual(uri, str(p))
        self.assertEqual(unicodeuri, unicode(p))
        self.assertTrue(type(p.sockname) is unicode)

    def testUriParsingPyro(self):
        p = Pyro4.core.URI("PYRONAME:some_obj_name")
        self.assertEqual("PYRONAME", p.protocol)
        self.assertEqual("some_obj_name", p.object)
        self.assertIsNone(p.host)
        self.assertIsNone(p.sockname)
        self.assertIsNone(p.port)
        p = Pyro4.core.URI("PYRONAME:some_obj_name@host.com:9999")
        self.assertEqual("PYRONAME", p.protocol)
        self.assertEqual("some_obj_name", p.object)
        self.assertEqual("host.com", p.host)
        self.assertEqual(9999, p.port)

        p = Pyro4.core.URI("PYRO:12345@host.com:4444")
        self.assertEqual("PYRO", p.protocol)
        self.assertEqual("12345", p.object)
        self.assertEqual("host.com", p.host)
        self.assertIsNone(p.sockname)
        self.assertEqual(4444, p.port)
        self.assertEqual("host.com:4444", p.location)
        p = Pyro4.core.URI("PYRO:12345@./u:sockname")
        self.assertEqual("12345", p.object)
        self.assertEqual("sockname", p.sockname)
        p = Pyro4.core.URI("PYRO:12345@./u:/tmp/sockname")
        self.assertEqual("12345", p.object)
        self.assertEqual("/tmp/sockname", p.sockname)
        p = Pyro4.core.URI("PYRO:12345@./u:../sockname")
        self.assertEqual("12345", p.object)
        self.assertEqual("../sockname", p.sockname)
        p = Pyro4.core.URI("pyro:12345@host.com:4444")
        self.assertEqual("PYRO", p.protocol)
        self.assertEqual("12345", p.object)
        self.assertEqual("host.com", p.host)
        self.assertIsNone(p.sockname)
        self.assertEqual(4444, p.port)
        p = Pyro4.core.URI("pyro:12345@[::1]:4444")
        self.assertEqual("::1", p.host)
        self.assertEqual("[::1]:4444", p.location)
        with self.assertRaises(Pyro4.errors.PyroError) as e:
            Pyro4.core.URI("pyro:12345@[[::1]]:4444")
        self.assertEqual("invalid ipv6 address: enclosed in too many brackets", str(e.exception))

    def testUriParsingPyroname(self):
        p = Pyro4.core.URI("PYRONAME:objectname")
        self.assertEqual("PYRONAME", p.protocol)
        self.assertEqual("objectname", p.object)
        self.assertIsNone(p.host)
        self.assertIsNone(p.port)
        p = Pyro4.core.URI("PYRONAME:objectname@nameserverhost")
        self.assertEqual("PYRONAME", p.protocol)
        self.assertEqual("objectname", p.object)
        self.assertEqual("nameserverhost", p.host)
        self.assertEqual(Pyro4.config.NS_PORT, p.port)  # Pyroname uri with host gets a port too if not specified
        p = Pyro4.core.URI("PYRONAME:objectname@nameserverhost:4444")
        self.assertEqual("PYRONAME", p.protocol)
        self.assertEqual("objectname", p.object)
        self.assertEqual("nameserverhost", p.host)
        self.assertEqual(4444, p.port)
        p = Pyro4.core.URI("PyroName:some_obj_name@host.com:9999")
        self.assertEqual("PYRONAME", p.protocol)
        p = Pyro4.core.URI("pyroname:some_obj_name@host.com:9999")
        self.assertEqual("PYRONAME", p.protocol)

    def testInvalidUris(self):
        self.assertRaises(TypeError, Pyro4.core.URI, None)
        self.assertRaises(TypeError, Pyro4.core.URI, 99999)
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "a")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYR")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO::")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:a")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:x@")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:x@hostname")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:@hostname:portstr")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:@hostname:7766")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:objid@hostname:7766:bogus")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYROLOC:objname")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYROLOC:objname@host")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYROLOC:objectname@hostname:4444")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRONAME:")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRONAME:objname@nameserver:bogus")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRONAME:objname@nameserver:7766:bogus")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "FOOBAR:")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "FOOBAR:objid@hostname:7766")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:12345@./u:sockname:9999")

    def testUriUnicode(self):
        p = Pyro4.core.URI(unicode("PYRO:12345@host.com:4444"))
        self.assertEqual("PYRO", p.protocol)
        self.assertEqual("12345", p.object)
        self.assertEqual("host.com", p.host)
        self.assertTrue(type(p.protocol) is unicode)
        self.assertTrue(type(p.object) is unicode)
        self.assertTrue(type(p.host) is unicode)
        self.assertIsNone(p.sockname)
        self.assertEqual(4444, p.port)

        uri = "PYRO:12345@hostname:9999"
        p = Pyro4.core.URI(uri)
        pu = Pyro4.core.URI(unicode(uri))
        self.assertEqual("PYRO", pu.protocol)
        self.assertEqual("hostname", pu.host)
        self.assertEqual(p, pu)
        self.assertEqual(str(p), str(pu))
        unicodeuri = "PYRO:weirdchars" + unichr(0x20ac) + "@host" + unichr(0x20AC) + ".com:4444"
        pu = Pyro4.core.URI(unicodeuri)
        self.assertEqual("PYRO", pu.protocol)
        self.assertEqual("host" + unichr(0x20AC) + ".com", pu.host)
        self.assertEqual("weirdchars" + unichr(0x20AC), pu.object)
        if sys.version_info <= (3, 0):
            self.assertEqual("PYRO:weirdchars?@host?.com:4444", pu.__str__())
            expected = "<Pyro4.core.URI at 0x%x, PYRO:weirdchars?@host?.com:4444>" % id(pu)
            self.assertEqual(expected, repr(pu))
        else:
            self.assertEqual("PYRO:weirdchars" + unichr(0x20ac) + "@host" + unichr(0x20ac) + ".com:4444", pu.__str__())
            expected = ("<Pyro4.core.URI at 0x%x, PYRO:weirdchars" + unichr(0x20ac) + "@host" + unichr(0x20ac) + ".com:4444>") % id(pu)
            self.assertEqual(expected, repr(pu))
        self.assertEqual("PYRO:weirdchars" + unichr(0x20ac) + "@host" + unichr(0x20ac) + ".com:4444", pu.asString())
        self.assertEqual("PYRO:weirdchars" + unichr(0x20ac) + "@host" + unichr(0x20ac) + ".com:4444", unicode(pu))

    def testUriCopy(self):
        p1 = Pyro4.core.URI("PYRO:12345@hostname:9999")
        p2 = Pyro4.core.URI(p1)
        p3 = copy.copy(p1)
        self.assertEqual(p1.protocol, p2.protocol)
        self.assertEqual(p1.host, p2.host)
        self.assertEqual(p1.port, p2.port)
        self.assertEqual(p1.object, p2.object)
        self.assertEqual(p1, p2)
        self.assertEqual(p1.protocol, p3.protocol)
        self.assertEqual(p1.host, p3.host)
        self.assertEqual(p1.port, p3.port)
        self.assertEqual(p1.object, p3.object)
        self.assertEqual(p1, p3)

    def testUriEqual(self):
        p1 = Pyro4.core.URI("PYRO:12345@host.com:9999")
        p2 = Pyro4.core.URI("PYRO:12345@host.com:9999")
        p3 = Pyro4.core.URI("PYRO:99999@host.com:4444")
        self.assertEqual(p1, p2)
        self.assertNotEqual(p1, p3)
        self.assertNotEqual(p2, p3)
        self.assertTrue(p1 == p2)
        self.assertFalse(p1 == p3)
        self.assertFalse(p2 == p3)
        self.assertFalse(p1 != p2)
        self.assertTrue(p1 != p3)
        self.assertTrue(p2 != p3)
        self.assertTrue(hash(p1) == hash(p2))
        self.assertTrue(hash(p1) != hash(p3))
        p2.port = 4444
        p2.object = "99999"
        self.assertNotEqual(p1, p2)
        self.assertEqual(p2, p3)
        self.assertFalse(p1 == p2)
        self.assertTrue(p2 == p3)
        self.assertTrue(p1 != p2)
        self.assertFalse(p2 != p3)
        self.assertTrue(hash(p1) != hash(p2))
        self.assertTrue(hash(p2) == hash(p3))
        self.assertFalse(p1 == 42)
        self.assertTrue(p1 != 42)

    def testLocation(self):
        self.assertTrue(Pyro4.core.URI.isUnixsockLocation("./u:name"))
        self.assertFalse(Pyro4.core.URI.isUnixsockLocation("./p:name"))
        self.assertFalse(Pyro4.core.URI.isUnixsockLocation("./x:name"))
        self.assertFalse(Pyro4.core.URI.isUnixsockLocation("foobar"))

    def testProxyCopy(self):
        u = Pyro4.core.URI("PYRO:12345@hostname:9999")
        p1 = Pyro4.core.Proxy(u)
        p2 = copy.copy(p1)  # check that most basic copy also works
        self.assertEqual(p1, p2)
        self.assertEqual(set(), p2._pyroOneway)
        p1._pyroAttrs = set("abc")
        p1._pyroTimeout = 42
        p1._pyroOneway = set("def")
        p1._pyroMethods = set("ghi")
        p2 = copy.copy(p1)
        self.assertEqual(p1, p2)
        self.assertEqual(p1._pyroUri, p2._pyroUri)
        self.assertEqual(p1._pyroOneway, p2._pyroOneway)
        self.assertEqual(p1._pyroMethods, p2._pyroMethods)
        self.assertEqual(p1._pyroAttrs, p2._pyroAttrs)
        self.assertEqual(p1._pyroTimeout, p2._pyroTimeout)

    def testProxyOffline(self):
        # only offline stuff here.
        # online stuff needs a running daemon, so we do that in another test, to keep this one simple
        self.assertRaises(TypeError, Pyro4.core.Proxy, 999)  # wrong arg
        p1 = Pyro4.core.Proxy("PYRO:9999@localhost:15555")
        p2 = Pyro4.core.Proxy(Pyro4.core.URI("PYRO:9999@localhost:15555"))
        self.assertEqual(p1._pyroUri, p2._pyroUri)
        self.assertIsNone(p1._pyroConnection)
        p1._pyroRelease()
        p1._pyroRelease()
        # try copying a not-connected proxy
        p3 = copy.copy(p1)
        self.assertIsNone(p3._pyroConnection)
        self.assertIsNone(p1._pyroConnection)
        self.assertEqual(p3._pyroUri, p1._pyroUri)
        self.assertIsNot(p3._pyroUri, p1._pyroUri)

    def testProxyRepr(self):
        p = Pyro4.core.Proxy("PYRO:9999@localhost:15555")
        address = id(p)
        expected = "<Pyro4.core.Proxy at 0x%x, not connected, for PYRO:9999@localhost:15555>" % address
        self.assertEqual(expected, repr(p))
        self.assertEqual(unicode(expected), unicode(p))

    def testProxyDir(self):
        # PyPy tries to call deprecated __members__ and __methods__
        # that causes a CommunicationError since we use a fake URI
        class ProxyWithFixedGettattr(Pyro4.core.Proxy):
            def __getattr__(self, name):
                if name in ('__members__', '__methods__'):
                    raise AttributeError(name)
                return super(Pyro4.core.Proxy, self).__getattr__(name)
        ProxyClass = ProxyWithFixedGettattr if 'pypy' in sys.version.lower() else Pyro4.core.Proxy
        p = ProxyClass("PYRO:9999@localhost:15555")
        # make sure that __dir__ implementation works the same way as dir()
        dir_result = dir(p)
        if sys.version_info < (3, 3):
            # before 3.3 python's object class didn't have __dir__ method
            dir_result.remove('__dir__')
        old_dir_method = getattr(Pyro4.core.Proxy, '__dir__')
        try:
            delattr(Pyro4.core.Proxy, '__dir__')
            self.assertEqual(dir_result, dir(p))
        finally:
            setattr(Pyro4.core.Proxy, '__dir__', old_dir_method)

    def testProxyDirMetadata(self):
        p = Pyro4.core.Proxy("PYRO:9999@localhost:15555")
        # metadata isn't loaded
        self.assertIn('__hash__', dir(p))
        self.assertNotIn('ping', dir(p))
        # emulate obtaininng metadata
        p._pyroAttrs = set(['prop'])
        p._pyroMethods = set(['ping'])
        self.assertIn('__hash__', dir(p))
        self.assertIn('prop', dir(p))
        self.assertIn('ping', dir(p))

    def testProxySettings(self):
        p1 = Pyro4.core.Proxy("PYRO:9999@localhost:15555")
        p2 = Pyro4.core.Proxy("PYRO:9999@localhost:15555")
        p1._pyroOneway.add("method")
        p1._pyroAttrs.add("attr")
        p1._pyroMethods.add("method2")
        self.assertIn("method", p1._pyroOneway)
        self.assertIn("attr", p1._pyroAttrs)
        self.assertIn("method2", p1._pyroMethods)
        self.assertNotIn("method", p2._pyroOneway)
        self.assertNotIn("attr", p2._pyroAttrs)
        self.assertNotIn("method2", p2._pyroMethods)
        self.assertIsNot(p1._pyroOneway, p2._pyroOneway, "p1 and p2 should have different oneway tables")
        self.assertIsNot(p1._pyroAttrs, p2._pyroAttrs, "p1 and p2 should have different attr tables")
        self.assertIsNot(p1._pyroMethods, p2._pyroMethods, "p1 and p2 should have different method tables")

    def testProxyWithStmt(self):
        class ConnectionMock(object):
            closeCalled = False

            def close(self):
                self.closeCalled = True

        connMock = ConnectionMock()
        # first without a 'with' statement
        p = Pyro4.core.Proxy("PYRO:9999@localhost:15555")
        p._pyroConnection = connMock
        self.assertFalse(connMock.closeCalled)
        p._pyroRelease()
        self.assertIsNone(p._pyroConnection)
        self.assertTrue(connMock.closeCalled)

        connMock = ConnectionMock()
        with Pyro4.core.Proxy("PYRO:9999@localhost:15555") as p:
            p._pyroConnection = connMock
        self.assertIsNone(p._pyroConnection)
        self.assertTrue(connMock.closeCalled)
        connMock = ConnectionMock()
        try:
            with Pyro4.core.Proxy("PYRO:9999@localhost:15555") as p:
                p._pyroConnection = connMock
                print(1 // 0)  # cause an error
            self.fail("expected error")
        except ZeroDivisionError:
            pass
        self.assertIsNone(p._pyroConnection)
        self.assertTrue(connMock.closeCalled)
        p = Pyro4.core.Proxy("PYRO:9999@localhost:15555")
        with p:
            self.assertIsNotNone(p._pyroUri)
        with p:
            self.assertIsNotNone(p._pyroUri)

    def testNoConnect(self):
        wrongUri = Pyro4.core.URI("PYRO:foobar@localhost:59999")
        with Pyro4.core.Proxy(wrongUri) as p:
            try:
                p.ping()
                self.fail("CommunicationError expected")
            except Pyro4.errors.CommunicationError:
                pass

    def testTimeoutGetSet(self):
        class ConnectionMock(object):
            def __init__(self):
                self.timeout = Pyro4.config.COMMTIMEOUT

            def close(self):
                pass

        Pyro4.config.COMMTIMEOUT = None
        p = Pyro4.core.Proxy("PYRO:obj@host:555")
        self.assertIsNone(p._pyroTimeout)
        p._pyroTimeout = 5
        self.assertEqual(5, p._pyroTimeout)
        p = Pyro4.core.Proxy("PYRO:obj@host:555")
        p._pyroConnection = ConnectionMock()
        self.assertIsNone(p._pyroTimeout)
        p._pyroTimeout = 5
        self.assertEqual(5, p._pyroTimeout)
        self.assertEqual(5, p._pyroConnection.timeout)
        Pyro4.config.COMMTIMEOUT = 2
        p = Pyro4.core.Proxy("PYRO:obj@host:555")
        p._pyroConnection = ConnectionMock()
        self.assertEqual(2, p._pyroTimeout)
        self.assertEqual(2, p._pyroConnection.timeout)
        p._pyroTimeout = None
        self.assertIsNone(p._pyroTimeout)
        self.assertIsNone(p._pyroConnection.timeout)
        Pyro4.config.COMMTIMEOUT = None

    def testCallbackDecorator(self):
        # just test the decorator itself, testing the callback
        # exception handling is kinda hard in unit tests. Maybe later.
        class Test(object):
            @Pyro4.callback
            def method(self):
                pass

            def method2(self):
                pass

        t = Test()
        self.assertEqual(True, getattr(t.method, "_pyroCallback"))
        self.assertEqual(False, getattr(t.method2, "_pyroCallback", False))

    def testProxyEquality(self):
        p1 = Pyro4.core.Proxy("PYRO:thing@localhost:15555")
        p2 = Pyro4.core.Proxy("PYRO:thing@localhost:15555")
        p3 = Pyro4.core.Proxy("PYRO:other@machine:16666")
        self.assertTrue(p1 == p2)
        self.assertFalse(p1 != p2)
        self.assertFalse(p1 == p3)
        self.assertTrue(p1 != p3)
        self.assertTrue(hash(p1) == hash(p2))
        self.assertFalse(hash(p1) == hash(p3))
        self.assertFalse(p1 == 42)
        self.assertTrue(p1 != 42)


class RemoteMethodTests(unittest.TestCase):
    class BatchProxyMock(object):
        def __init__(self):
            self.result = []

        def __copy__(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def _pyroBatch(self):
            return Pyro4.core._BatchProxyAdapter(self)

        def _pyroInvokeBatch(self, calls, oneway=False):
            self.result = []
            for methodname, args, kwargs in calls:
                if methodname == "error":
                    self.result.append(Pyro4.futures._ExceptionWrapper(ValueError("some exception")))
                    break  # stop processing the rest, this is what Pyro should do in case of an error in a batch
                elif methodname == "pause":
                    time.sleep(args[0])
                self.result.append("INVOKED %s args=%s kwargs=%s" % (methodname, args, kwargs))
            if oneway:
                return
            else:
                return self.result

    class AsyncProxyMock(object):
        def __copy__(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def _pyroAsync(self):
            return Pyro4.core._AsyncProxyAdapter(self)

        def _pyroInvoke(self, methodname, vargs, kwargs, flags=0):
            if methodname == "pause_and_divide":
                time.sleep(vargs[0])
                return vargs[1] // vargs[2]
            else:
                raise NotImplementedError(methodname)

    def setUp(self):
        Pyro4.config.HMAC_KEY = b"testsuite"

    def tearDown(self):
        Pyro4.config.HMAC_KEY = None

    def testRemoteMethodMetaOff(self):
        try:
            Pyro4.config.METADATA = False
            class ProxyMock(object):
                def invoke(self, name, args, kwargs):
                    return "INVOKED name=%s args=%s kwargs=%s" % (name, args, kwargs)

                def __getattr__(self, name):
                    return Pyro4.core._RemoteMethod(self.invoke, name)

            o = ProxyMock()
            self.assertEqual("INVOKED name=foo args=(1,) kwargs={}", o.foo(1))  # normal
            self.assertEqual("INVOKED name=foo.bar args=(1,) kwargs={}", o.foo.bar(1))  # dotted
            self.assertEqual("INVOKED name=foo.bar args=(1, 'hello') kwargs={'a': True}", o.foo.bar(1, "hello", a=True))
            p = Pyro4.core.Proxy("PYRO:obj@host:666")
            a = p.someattribute
            self.assertIsInstance(a, Pyro4.core._RemoteMethod, "attribute access should just be a RemoteMethod")
            a2 = a.nestedattribute.nested2
            self.assertIsInstance(a2, Pyro4.core._RemoteMethod, "nested attribute should just be another RemoteMethod")
        finally:
            Pyro4.config.METADATA = True

    def testRemoteMethodMetaOn(self):
        p = Pyro4.core.Proxy("PYRO:obj@localhost:59999")
        with self.assertRaises(Pyro4.errors.CommunicationError):
            _ = p.someattribute     # triggers attempt to get metadata

    def testBatchMethod(self):
        proxy = self.BatchProxyMock()
        batch = Pyro4.batch(proxy)
        self.assertIsNone(batch.foo(42))
        self.assertIsNone(batch.bar("abc"))
        self.assertIsNone(batch.baz(42, "abc", arg=999))
        self.assertIsNone(batch.error())  # generate an exception
        self.assertIsNone(batch.foo(42))  # this call should not be performed after the error
        results = batch()
        result = next(results)
        self.assertEqual("INVOKED foo args=(42,) kwargs={}", result)
        result = next(results)
        self.assertEqual("INVOKED bar args=('abc',) kwargs={}", result)
        result = next(results)
        self.assertEqual("INVOKED baz args=(42, 'abc') kwargs={'arg': 999}", result)
        self.assertRaises(ValueError, next, results)  # the call to error() should generate an exception
        self.assertRaises(StopIteration, next, results)  # and now there should not be any more results
        self.assertEqual(4, len(proxy.result))  # should have done 4 calls, not 5

    def testBatchMethodOneway(self):
        proxy = self.BatchProxyMock()
        batch = Pyro4.batch(proxy)
        self.assertIsNone(batch.foo(42))
        self.assertIsNone(batch.bar("abc"))
        self.assertIsNone(batch.baz(42, "abc", arg=999))
        self.assertIsNone(batch.error())  # generate an exception
        self.assertIsNone(batch.foo(42))  # this call should not be performed after the error
        results = batch(oneway=True)
        self.assertIsNone(results)  # oneway always returns None
        self.assertEqual(4, len(proxy.result))  # should have done 4 calls, not 5
        self.assertRaises(Pyro4.errors.PyroError, batch, oneway=True, async=True)  # oneway+async=booboo

    def testBatchMethodAsync(self):
        proxy = self.BatchProxyMock()
        batch = Pyro4.batch(proxy)
        self.assertIsNone(batch.foo(42))
        self.assertIsNone(batch.bar("abc"))
        self.assertIsNone(batch.pause(0.5))  # pause shouldn't matter with async
        self.assertIsNone(batch.baz(42, "abc", arg=999))
        begin = time.time()
        asyncresult = batch(async=True)
        duration = time.time() - begin
        self.assertLess(duration, 0.1, "batch oneway with pause should still return almost immediately")
        results = asyncresult.value
        self.assertEqual(4, len(proxy.result))  # should have done 4 calls
        result = next(results)
        self.assertEqual("INVOKED foo args=(42,) kwargs={}", result)
        result = next(results)
        self.assertEqual("INVOKED bar args=('abc',) kwargs={}", result)
        result = next(results)
        self.assertEqual("INVOKED pause args=(0.5,) kwargs={}", result)
        result = next(results)
        self.assertEqual("INVOKED baz args=(42, 'abc') kwargs={'arg': 999}", result)
        self.assertRaises(StopIteration, next, results)  # and now there should not be any more results

    def testBatchMethodReuse(self):
        proxy = self.BatchProxyMock()
        batch = Pyro4.batch(proxy)
        batch.foo(1)
        batch.foo(2)
        results = batch()
        self.assertEqual(['INVOKED foo args=(1,) kwargs={}', 'INVOKED foo args=(2,) kwargs={}'], list(results))
        # re-use the batch proxy:
        batch.foo(3)
        batch.foo(4)
        results = batch()
        self.assertEqual(['INVOKED foo args=(3,) kwargs={}', 'INVOKED foo args=(4,) kwargs={}'], list(results))
        results = batch()
        self.assertEqual(0, len(list(results)))

    def testAsyncMethod(self):
        proxy = self.AsyncProxyMock()
        async = Pyro4.async(proxy)
        begin = time.time()
        result = async.pause_and_divide(0.2, 10, 2)  # returns immediately
        duration = time.time() - begin
        self.assertLess(duration, 0.1)
        self.assertFalse(result.ready)
        _ = result.value
        self.assertTrue(result.ready)

    def testAsyncCallbackMethod(self):
        class AsyncFunctionHolder(object):
            asyncFunctionCount = 0

            def asyncFunction(self, value, amount=1):
                self.asyncFunctionCount += 1
                return value + amount

        proxy = self.AsyncProxyMock()
        async = Pyro4.async(proxy)
        result = async.pause_and_divide(0.2, 10, 2)  # returns immediately
        holder = AsyncFunctionHolder()
        result.then(holder.asyncFunction, amount=2) \
            .then(holder.asyncFunction, amount=4) \
            .then(holder.asyncFunction)
        value = result.value
        self.assertEqual(10 // 2 + 2 + 4 + 1, value)
        self.assertEqual(3, holder.asyncFunctionCount)

    def testCrashingAsyncCallbackMethod(self):
        def normalAsyncFunction(value, x):
            return value + x

        def crashingAsyncFunction(value):
            return 1 // 0  # crash

        proxy = self.AsyncProxyMock()
        async = Pyro4.async(proxy)
        result = async.pause_and_divide(0.2, 10, 2)  # returns immediately
        result.then(crashingAsyncFunction).then(normalAsyncFunction, 2)
        try:
            _ = result.value
            self.fail("expected exception")
        except ZeroDivisionError:
            pass  # ok

    def testAsyncMethodTimeout(self):
        proxy = self.AsyncProxyMock()
        async = Pyro4.async(proxy)
        result = async.pause_and_divide(1, 10, 2)  # returns immediately
        self.assertFalse(result.ready)
        self.assertFalse(result.wait(0.5))  # won't be ready after 0.5 sec
        self.assertTrue(result.wait(1))  # will be ready within 1 seconds more
        self.assertTrue(result.ready)
        self.assertEqual(5, result.value)


class TestSimpleServe(unittest.TestCase):
    class DaemonWrapper(Pyro4.core.Daemon):
        def requestLoop(self, *args):
            # override with empty method to fall out of the serveSimple call
            pass

    def testSimpleServe(self):
        with TestSimpleServe.DaemonWrapper() as d:
            o1 = MyThing(1)
            o2 = MyThing(2)
            objects = {o1: "test.o1", o2: None}
            Pyro4.core.Daemon.serveSimple(objects, daemon=d, ns=False, verbose=False)
            self.assertEqual(3, len(d.objectsById))
            self.assertIn("test.o1", d.objectsById)
            self.assertIn(o1, d.objectsById.values())
            self.assertIn(o2, d.objectsById.values())

    def testSimpleServeSameNames(self):
        with TestSimpleServe.DaemonWrapper() as d:
            o1 = MyThing(1)
            o2 = MyThing(2)
            o3 = MyThing(3)
            objects = {o1: "test.name", o2: "test.name", o3: "test.othername"}
            with self.assertRaises(Pyro4.errors.DaemonError):
                Pyro4.core.Daemon.serveSimple(objects, daemon=d, ns=False, verbose=False)


def futurestestfunc(a, b, extra=None):
    if extra is None:
        return a + b
    else:
        return a + b + extra


def crashingfuturestestfunc(a):
    return 1 // 0  # crash


class TestFutures(unittest.TestCase):
    def testSimpleFuture(self):
        f = Pyro4.Future(futurestestfunc)
        r = f(4, 5)
        self.assertIsInstance(r, Pyro4.futures.FutureResult)
        value = r.value
        self.assertEqual(9, value)

    def testFutureChain(self):
        f = Pyro4.Future(futurestestfunc)
        f.then(futurestestfunc, 6)
        f.then(futurestestfunc, 7, extra=10)
        r = f(4, 5)
        value = r.value
        self.assertEqual(4 + 5 + 6 + 7 + 10, value)

    def testCrashingChain(self):
        f = Pyro4.Future(futurestestfunc)
        f.then(futurestestfunc, 6)
        f.then(crashingfuturestestfunc)
        f.then(futurestestfunc, 8)
        r = f(4, 5)
        try:
            _ = r.value
            self.fail("expected exception")
        except ZeroDivisionError:
            pass  # ok


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
