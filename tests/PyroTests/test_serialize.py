"""
Tests for the data serializer.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import array
import sys
import collections
import copy
import pprint
import pickle
import base64
import unittest
import serpent
import math
import uuid
import Pyro4.util
import Pyro4.errors
import Pyro4.core
import Pyro4.futures
from Pyro4.configuration import config
from testsupport import *


class SerializeTests_pickle(unittest.TestCase):
    SERIALIZER = "pickle"

    def setUp(self):
        self.previous_serializer = config.SERIALIZER
        config.SERIALIZER = self.SERIALIZER
        self.serializer = Pyro4.util.get_serializer(config.SERIALIZER)
        config.REQUIRE_EXPOSE = True

    def tearDown(self):
        config.SERIALIZER = self.previous_serializer

    def testSerItself(self):
        s = Pyro4.util.get_serializer(config.SERIALIZER)
        p, _ = self.serializer.serializeData(s)
        s2 = self.serializer.deserializeData(p)
        self.assertEqual(s, s2)
        self.assertTrue(s == s2)
        self.assertFalse(s != s2)

    def testSerUnicode(self):
        data = unicode("x")
        self.serializer.serializeData(data)
        self.serializer.serializeCall(data, unicode("method"), [], {})

    def testSerCompression(self):
        d1, c1 = self.serializer.serializeData("small data", compress=True)
        d2, c2 = self.serializer.serializeData("small data", compress=False)
        self.assertFalse(c1)
        self.assertEqual(d1, d2)
        bigdata = "x" * 1000
        d1, c1 = self.serializer.serializeData(bigdata, compress=False)
        d2, c2 = self.serializer.serializeData(bigdata, compress=True)
        self.assertFalse(c1)
        self.assertTrue(c2)
        self.assertTrue(len(d2) < len(d1))
        self.assertEqual(bigdata, self.serializer.deserializeData(d1, compressed=False))
        self.assertEqual(bigdata, self.serializer.deserializeData(d2, compressed=True))

    def testSerErrors(self):
        e1 = Pyro4.errors.NamingError(unicode("x"))
        e1._pyroTraceback = ["this is the remote traceback"]
        orig_e = copy.copy(e1)
        e2 = Pyro4.errors.PyroError(unicode("x"))
        e3 = Pyro4.errors.ProtocolError(unicode("x"))
        if sys.platform == "cli":
            Pyro4.util.fixIronPythonExceptionForPickle(e1, True)
        p, _ = self.serializer.serializeData(e1)
        e = self.serializer.deserializeData(p)
        if sys.platform == "cli":
            Pyro4.util.fixIronPythonExceptionForPickle(e, False)
        self.assertIsInstance(e, Pyro4.errors.NamingError)
        self.assertEqual(repr(orig_e), repr(e))
        self.assertEqual(["this is the remote traceback"], e._pyroTraceback, "remote traceback info should be present")
        p, _ = self.serializer.serializeData(e2)
        e = self.serializer.deserializeData(p)
        self.assertIsInstance(e, Pyro4.errors.PyroError)
        self.assertEqual(repr(e2), repr(e))
        p, _ = self.serializer.serializeData(e3)
        e = self.serializer.deserializeData(p)
        self.assertIsInstance(e, Pyro4.errors.ProtocolError)
        self.assertEqual(repr(e3), repr(e))

    def testSerializeExceptionWithAttr(self):
        ex = ZeroDivisionError("test error")
        ex._pyroTraceback = ["test traceback payload"]
        Pyro4.util.fixIronPythonExceptionForPickle(ex, True)  # hack for ironpython
        data, compressed = self.serializer.serializeData(ex)
        ex2 = self.serializer.deserializeData(data, compressed)
        Pyro4.util.fixIronPythonExceptionForPickle(ex2, False)  # hack for ironpython
        self.assertEqual(ZeroDivisionError, type(ex2))
        self.assertTrue(hasattr(ex2, "_pyroTraceback"))
        self.assertEqual(["test traceback payload"], ex2._pyroTraceback)

    def testSerCoreOffline(self):
        uri = Pyro4.core.URI("PYRO:9999@host.com:4444")
        p, _ = self.serializer.serializeData(uri)
        uri2 = self.serializer.deserializeData(p)
        self.assertEqual(uri, uri2)
        self.assertEqual("PYRO", uri2.protocol)
        self.assertEqual("9999", uri2.object)
        self.assertEqual("host.com:4444", uri2.location)
        self.assertEqual(4444, uri2.port)
        self.assertIsNone(uri2.sockname)

        uri = Pyro4.core.URI("PYRO:12345@./u:/tmp/socketname")
        p, _ = self.serializer.serializeData(uri)
        uri2 = self.serializer.deserializeData(p)
        self.assertEqual(uri, uri2)
        self.assertEqual("PYRO", uri2.protocol)
        self.assertEqual("12345", uri2.object)
        self.assertEqual("./u:/tmp/socketname", uri2.location)
        self.assertIsNone(uri2.port)
        self.assertEqual("/tmp/socketname", uri2.sockname)

        proxy = Pyro4.core.Proxy("PYRO:9999@host.com:4444")
        proxy._pyroTimeout = 42
        proxy._pyroMaxRetries = 78
        self.assertIsNone(proxy._pyroConnection)
        p, _ = self.serializer.serializeData(proxy)
        proxy2 = self.serializer.deserializeData(p)
        self.assertIsNone(proxy._pyroConnection)
        self.assertIsNone(proxy2._pyroConnection)
        self.assertEqual(proxy2._pyroUri, proxy._pyroUri)
        self.assertEqual(0, proxy2._pyroTimeout, "must be reset to defaults")
        self.assertEqual(0, proxy2._pyroMaxRetries, "must be reset to defaults")

    def testNested(self):
        if self.SERIALIZER == "marshal":
            self.skipTest("marshal can't serialize custom objects")
        uri1 = Pyro4.core.URI("PYRO:1111@host.com:111")
        uri2 = Pyro4.core.URI("PYRO:2222@host.com:222")
        _ = self.serializer.serializeData(uri1)
        data = [uri1, uri2]
        p, _ = self.serializer.serializeData(data)
        [u1, u2] = self.serializer.deserializeData(p)
        self.assertEqual(uri1, u1)
        self.assertEqual(uri2, u2)

    def testSerDaemonHack(self):
        # This tests the hack that a Daemon should be serializable,
        # but only to support serializing Pyro objects.
        # The serialized form of a Daemon should be empty (and thus, useless)
        with Pyro4.core.Daemon(port=0) as daemon:
            d, _ = self.serializer.serializeData(daemon)
            d2 = self.serializer.deserializeData(d)
            self.assertTrue(len(d2.__dict__) == 0, "deserialized daemon should be empty")
            self.assertTrue("Pyro4.core.Daemon" in repr(d2))
            self.assertTrue("unusable" in repr(d2))
            try:
                config.AUTOPROXY = False
                obj = pprint.PrettyPrinter(stream="dummy", width=42)
                obj.name = "hello"
                daemon.register(obj)
                o, _ = self.serializer.serializeData(obj)
                if self.SERIALIZER in ("pickle", "cloudpickle", "dill"):
                    # only pickle, cloudpickle and dill can deserialize the PrettyPrinter class without the need of explicit deserialization function
                    o2 = self.serializer.deserializeData(o)
                    self.assertEqual("hello", o2.name)
                    self.assertEqual(42, o2._width)
            finally:
                config.AUTOPROXY = True

    def testPyroClasses(self):
        uri = Pyro4.core.URI("PYRO:object@host:4444")
        s, c = self.serializer.serializeData(uri)
        x = self.serializer.deserializeData(s, c)
        self.assertIsInstance(x, Pyro4.core.URI)
        self.assertEqual(uri, x)
        self.assertTrue("Pyro4.core.URI" in repr(uri))
        self.assertEqual("PYRO:object@host:4444", str(uri))
        uri = Pyro4.core.URI("PYRO:12345@./u:/tmp/socketname")
        s, c = self.serializer.serializeData(uri)
        x = self.serializer.deserializeData(s, c)
        self.assertIsInstance(x, Pyro4.core.URI)
        self.assertEqual(uri, x)
        proxy = Pyro4.core.Proxy(uri)
        proxy._pyroAttrs = set("abc")
        proxy._pyroMethods = set("def")
        proxy._pyroOneway = set("ghi")
        proxy._pyroTimeout = 42
        proxy._pyroHmacKey = b"secret"
        proxy._pyroHandshake = "apples"
        proxy._pyroMaxRetries = 78
        proxy._pyroSerializer = "serializer"
        s, c = self.serializer.serializeData(proxy)
        x = self.serializer.deserializeData(s, c)
        self.assertIsInstance(x, Pyro4.core.Proxy)
        self.assertEqual(proxy._pyroUri, x._pyroUri)
        self.assertEqual(set("abc"), x._pyroAttrs)
        self.assertEqual(set("def"), x._pyroMethods)
        self.assertEqual(set("ghi"), x._pyroOneway)
        self.assertEqual(b"secret", x._pyroHmacKey)
        self.assertEqual("apples", x._pyroHandshake)
        self.assertEqual("serializer", x._pyroSerializer)
        self.assertEqual(0, x._pyroTimeout, "must be reset to defaults")
        self.assertEqual(0, x._pyroMaxRetries, "must be reset to defaults")
        self.assertTrue("Pyro4.core.Proxy" in repr(x))
        self.assertTrue("Pyro4.core.Proxy" in str(x))
        daemon = Pyro4.core.Daemon()
        s, c = self.serializer.serializeData(daemon)
        x = self.serializer.deserializeData(s, c)
        self.assertIsInstance(x, Pyro4.core.Daemon)
        self.assertTrue("Pyro4.core.Daemon" in repr(x))
        self.assertTrue("unusable" in repr(x))
        self.assertTrue("Pyro4.core.Daemon" in str(x))
        self.assertTrue("unusable" in str(x))
        wrapper = Pyro4.futures._ExceptionWrapper(ZeroDivisionError("divided by zero"))
        s, c = self.serializer.serializeData(wrapper)
        x = self.serializer.deserializeData(s, c)
        self.assertIsInstance(x, Pyro4.futures._ExceptionWrapper)
        self.assertEqual("divided by zero", str(x.exception))
        self.assertTrue("ExceptionWrapper" in repr(x))
        self.assertTrue("ExceptionWrapper" in str(x))

    def testPyroClassesForDict(self):
        uri = Pyro4.core.URI("PYRO:object@host:4444")
        state = uri.__getstate_for_dict__()
        self.assertEqual(('PYRO', 'object', None, 'host', 4444), state)
        uri2 = Pyro4.core.URI("PYRONAME:xxx")
        uri2.__setstate_from_dict__(state)
        self.assertEqual(uri, uri2)
        proxy = Pyro4.core.Proxy(uri)
        proxy._pyroAttrs = set("abc")
        proxy._pyroMethods = set("def")
        proxy._pyroOneway = set("ghi")
        proxy._pyroTimeout = 42
        proxy._pyroHmacKey = b"secret"
        proxy._pyroHandshake = "apples"
        proxy._pyroMaxRetries = 78
        proxy._pyroSerializer = "serializer"
        state = proxy.__getstate_for_dict__()
        b64_secret = "b64:"+base64.b64encode(b"secret").decode("utf-8")
        self.assertEqual(('PYRO:object@host:4444', tuple(set("ghi")), tuple(set("def")), tuple(set("abc")), 42, b64_secret, "apples", 78, "serializer"), state)
        proxy2 = Pyro4.core.Proxy("PYRONAME:xxx")
        proxy2.__setstate_from_dict__(state)
        self.assertEqual(proxy, proxy2)
        self.assertEqual(proxy._pyroUri, proxy2._pyroUri)
        self.assertEqual(proxy._pyroAttrs, proxy2._pyroAttrs)
        self.assertEqual(proxy._pyroMethods, proxy2._pyroMethods)
        self.assertEqual(proxy._pyroOneway, proxy2._pyroOneway)
        self.assertEqual(proxy._pyroHmacKey, proxy2._pyroHmacKey)
        self.assertEqual(proxy._pyroHandshake, proxy2._pyroHandshake)
        self.assertEqual(proxy._pyroSerializer, proxy2._pyroSerializer)
        self.assertEqual(0, proxy2._pyroTimeout, "must be reset to defaults")
        self.assertEqual(0, proxy2._pyroMaxRetries, "must be reset to defaults")
        daemon = Pyro4.core.Daemon()
        state = daemon.__getstate_for_dict__()
        self.assertEqual(tuple(), state)
        daemon2 = Pyro4.core.Daemon()
        daemon2.__setstate_from_dict__(state)

    def testProxySerializationCompat(self):
        proxy = Pyro4.core.Proxy("PYRO:object@host:4444")
        proxy._pyroSerializer = "serializer"
        pickle_state = proxy.__getstate__()
        self.assertEqual(9, len(pickle_state))
        pickle_state = pickle_state[:8]
        proxy.__setstate__(pickle_state)
        self.assertIsNone(proxy._pyroSerializer)
        proxy._pyroSerializer = "serializer"
        serpent_state = proxy.__getstate_for_dict__()
        self.assertEqual(9, len(serpent_state))
        serpent_state = serpent_state[:8]
        proxy.__setstate_from_dict__(serpent_state)
        self.assertIsNone(proxy._pyroSerializer)

    def testAutoProxyPartlyExposed(self):
        if self.SERIALIZER == "marshal":
            self.skipTest("marshal can't serialize custom objects")
        self.serializer.register_type_replacement(MyThingPartlyExposed, Pyro4.core.pyroObjectToAutoProxy)
        t1 = MyThingPartlyExposed("1")
        t2 = MyThingPartlyExposed("2")
        with Pyro4.core.Daemon() as d:
            d.register(t1, "thingy1")
            d.register(t2, "thingy2")
            data = [t1, ["apple", t2]]
            s, c = self.serializer.serializeData(data)
            data = self.serializer.deserializeData(s, c)
            self.assertEqual("apple", data[1][0])
            p1 = data[0]
            p2 = data[1][1]
            self.assertIsInstance(p1, Pyro4.core.Proxy)
            self.assertIsInstance(p2, Pyro4.core.Proxy)
            self.assertEqual("thingy1", p1._pyroUri.object)
            self.assertEqual("thingy2", p2._pyroUri.object)
            self.assertEqual({"prop1", "readonly_prop1"}, p1._pyroAttrs)
            self.assertEqual({"exposed", "oneway"}, p1._pyroMethods)
            self.assertEqual({'oneway'}, p1._pyroOneway)

    def testAutoProxyFullExposed(self):
        if self.SERIALIZER == "marshal":
            self.skipTest("marshal can't serialize custom objects")
        self.serializer.register_type_replacement(MyThingPartlyExposed, Pyro4.core.pyroObjectToAutoProxy)
        t1 = MyThingFullExposed("1")
        t2 = MyThingFullExposed("2")
        with Pyro4.core.Daemon() as d:
            d.register(t1, "thingy1")
            d.register(t2, "thingy2")
            data = [t1, ["apple", t2]]
            s, c = self.serializer.serializeData(data)
            data = self.serializer.deserializeData(s, c)
            self.assertEqual("apple", data[1][0])
            p1 = data[0]
            p2 = data[1][1]
            self.assertIsInstance(p1, Pyro4.core.Proxy)
            self.assertIsInstance(p2, Pyro4.core.Proxy)
            self.assertEqual("thingy1", p1._pyroUri.object)
            self.assertEqual("thingy2", p2._pyroUri.object)
            self.assertEqual({"prop1", "prop2", "readonly_prop1"}, p1._pyroAttrs)
            self.assertEqual({'classmethod', 'method', 'oneway', 'staticmethod', 'exposed', "__dunder__"}, p1._pyroMethods)
            self.assertEqual({'oneway'}, p1._pyroOneway)

    def testRegisterTypeReplacementSanity(self):
        if self.SERIALIZER == "marshal":
            self.skipTest("marshal can't serialize custom objects")
        self.serializer.register_type_replacement(int, lambda: None)
        with self.assertRaises(ValueError):
            self.serializer.register_type_replacement(type, lambda: None)
        with self.assertRaises(ValueError):
            self.serializer.register_type_replacement(42, lambda: None)

    def testCustomClassFail(self):
        if self.SERIALIZER in ("pickle", "cloudpickle", "dill"):
            self.skipTest("pickle, cloudpickle and dill simply serialize custom classes")
        o = pprint.PrettyPrinter(stream="dummy", width=42)
        s, c = self.serializer.serializeData(o)
        try:
            _ = self.serializer.deserializeData(s, c)
            self.fail("error expected, shouldn't deserialize unknown class")
        except Pyro4.errors.ProtocolError:
            pass

    def testCustomClassOk(self):
        if self.SERIALIZER in ("pickle", "cloudpickle", "dill"):
            self.skipTest("pickle, cloudpickle and dill simply serialize custom classes just fine")
        o = MyThingPartlyExposed("test")
        Pyro4.util.SerializerBase.register_class_to_dict(MyThingPartlyExposed, mything_dict)
        Pyro4.util.SerializerBase.register_dict_to_class("CUSTOM-Mythingymabob", mything_creator)
        s, c = self.serializer.serializeData(o)
        o2 = self.serializer.deserializeData(s, c)
        self.assertIsInstance(o2, MyThingPartlyExposed)
        self.assertEqual("test", o2.name)
        # unregister the deserializer
        Pyro4.util.SerializerBase.unregister_dict_to_class("CUSTOM-Mythingymabob")
        try:
            self.serializer.deserializeData(s, c)
            self.fail("must fail")
        except Pyro4.errors.ProtocolError:
            pass  # ok
        # unregister the serializer
        Pyro4.util.SerializerBase.unregister_class_to_dict(MyThingPartlyExposed)
        s, c = self.serializer.serializeData(o)
        try:
            self.serializer.deserializeData(s, c)
            self.fail("must fail")
        except Pyro4.errors.SerializeError as x:
            msg = str(x)
            self.assertIn(msg, ["unsupported serialized class: testsupport.MyThingPartlyExposed",
                                "unsupported serialized class: PyroTests.testsupport.MyThingPartlyExposed"])

    def testData(self):
        data = [42, "hello"]
        ser, compressed = self.serializer.serializeData(data)
        self.assertFalse(compressed)
        data2 = self.serializer.deserializeData(ser, compressed=False)
        self.assertEqual(data, data2)

    def testUnicodeData(self):
        data = u"euro\u20aclowbytes\u0000\u0001\u007f\u0080\u00ff"
        ser, compressed = self.serializer.serializeData(data)
        data2 = self.serializer.deserializeData(ser, compressed=compressed)
        self.assertEqual(data, data2)

    def testUUID(self):
        data = uuid.uuid1()
        ser, compressed = self.serializer.serializeData(data)
        data2 = self.serializer.deserializeData(ser, compressed=compressed)
        uuid_as_str = str(data)
        self.assertTrue(data2==data or data2==uuid_as_str)

    def testSet(self):
        data = {111, 222, 333}
        ser, compressed = self.serializer.serializeData(data)
        data2 = self.serializer.deserializeData(ser, compressed=compressed)
        self.assertEqual(data, data2)

    def testCircular(self):
        data = [42, "hello", Pyro4.core.Proxy("PYRO:dummy@dummy:4444")]
        data.append(data)
        ser, compressed = self.serializer.serializeData(data)
        data2 = self.serializer.deserializeData(ser, compressed)
        self.assertIs(data2, data2[3])
        self.assertEqual(42, data2[0])

    def testCallPlain(self):
        ser, compressed = self.serializer.serializeCall("object", "method", ("vargs1", "vargs2"), {"kwargs": 999})
        self.assertFalse(compressed)
        obj, method, vargs, kwargs = self.serializer.deserializeCall(ser, compressed=False)
        self.assertEqual("object", obj)
        self.assertEqual("method", method)
        self.assertTrue(len(vargs) == 2)
        self.assertTrue(vargs[0] == "vargs1")
        self.assertTrue(vargs[1] == "vargs2")
        self.assertDictEqual({"kwargs": 999}, kwargs)

    def testCallPyroObjAsArg(self):
        if self.SERIALIZER == "marshal":
            self.skipTest("marshal can't serialize custom objects")
        uri = Pyro4.core.URI("PYRO:555@localhost:80")
        ser, compressed = self.serializer.serializeCall("object", "method", [uri], {"thing": uri})
        self.assertFalse(compressed)
        obj, method, vargs, kwargs = self.serializer.deserializeCall(ser, compressed=False)
        self.assertEqual("object", obj)
        self.assertEqual("method", method)
        self.assertEqual([uri], vargs)
        self.assertEqual({"thing": uri}, kwargs)

    def testCallCustomObjAsArg(self):
        if self.SERIALIZER == "marshal":
            self.skipTest("marshal can't serialize custom objects")
        e = ZeroDivisionError("hello")
        ser, compressed = self.serializer.serializeCall("object", "method", [e], {"thing": e})
        self.assertFalse(compressed)
        obj, method, vargs, kwargs = self.serializer.deserializeCall(ser, compressed=False)
        self.assertEqual("object", obj)
        self.assertEqual("method", method)
        self.assertIsInstance(vargs, list)
        self.assertIsInstance(vargs[0], ZeroDivisionError)
        self.assertEqual("hello", str(vargs[0]))
        self.assertIsInstance(kwargs["thing"], ZeroDivisionError)
        self.assertEqual("hello", str(kwargs["thing"]))

    def testSerializeException(self):
        e = ZeroDivisionError()
        d, c = self.serializer.serializeData(e)
        e2 = self.serializer.deserializeData(d, c)
        self.assertIsInstance(e2, ZeroDivisionError)
        self.assertEqual("", str(e2))
        e = ZeroDivisionError("hello")
        d, c = self.serializer.serializeData(e)
        e2 = self.serializer.deserializeData(d, c)
        self.assertIsInstance(e2, ZeroDivisionError)
        self.assertEqual("hello", str(e2))
        e = ZeroDivisionError("hello", 42)
        d, c = self.serializer.serializeData(e)
        e2 = self.serializer.deserializeData(d, c)
        self.assertIsInstance(e2, ZeroDivisionError)
        self.assertIn(str(e2), ("('hello', 42)", "(u'hello', 42)"))
        e.custom_attribute = 999
        if sys.platform == "cli":
            Pyro4.util.fixIronPythonExceptionForPickle(e, True)
        ser, compressed = self.serializer.serializeData(e)
        e2 = self.serializer.deserializeData(ser, compressed)
        if sys.platform == "cli":
            Pyro4.util.fixIronPythonExceptionForPickle(e2, False)
        self.assertIsInstance(e2, ZeroDivisionError)
        self.assertIn(str(e2), ("('hello', 42)", "(u'hello', 42)"))
        self.assertEqual(999, e2.custom_attribute)

    def testSerializeSpecialException(self):
        self.assertIn("GeneratorExit", Pyro4.util.all_exceptions)
        e = GeneratorExit()
        d, c = self.serializer.serializeData(e)
        e2 = self.serializer.deserializeData(d, c)
        self.assertIsInstance(e2, GeneratorExit)

    def testRecreateClasses(self):
        self.assertEqual([1, 2, 3], self.serializer.recreate_classes([1, 2, 3]))
        d = {"__class__": "invalid"}
        try:
            self.serializer.recreate_classes(d)
            self.fail("error expected")
        except Pyro4.errors.ProtocolError:
            pass  # ok
        d = {"__class__": "Pyro4.core.URI", "state": ['PYRO', '555', None, 'localhost', 80]}
        uri = self.serializer.recreate_classes(d)
        self.assertEqual(Pyro4.core.URI("PYRO:555@localhost:80"), uri)
        number, uri = self.serializer.recreate_classes([1, {"uri": d}])
        self.assertEqual(1, number)
        self.assertEqual(Pyro4.core.URI("PYRO:555@localhost:80"), uri["uri"])

    def testProtocolVersion(self):
        self.assertGreaterEqual(config.PICKLE_PROTOCOL_VERSION, 2)
        self.assertEqual(pickle.HIGHEST_PROTOCOL, config.PICKLE_PROTOCOL_VERSION)

    def testUriSerializationWithoutSlots(self):
        orig_protocol = config.PICKLE_PROTOCOL_VERSION
        config.PICKLE_PROTOCOL_VERSION = 2
        try:
            u = Pyro4.core.URI("PYRO:obj@localhost:1234")
            d, compr = self.serializer.serializeData(u)
            self.assertFalse(compr)
            import pickletools
            d = pickletools.optimize(d)
            result1 = b'\x80\x02cPyro4.core\nURI\n)\x81(U\x04PYROU\x03objNU\tlocalhostM\xd2\x04tb.'
            result2 = b'\x80\x02cPyro4.core\nURI\n)\x81(X\x04\x00\x00\x00PYROX\x03\x00\x00\x00objNX\t\x00\x00\x00localhostM\xd2\x04tb.'
            self.assertTrue(d in (result1, result2))
        finally:
            config.PICKLE_PROTOCOL_VERSION = orig_protocol

    def testFloatPrecision(self):
        f1 = 1482514078.54635912345
        f2 = 9876543212345.12345678987654321
        f3 = 11223344.556677889988776655e33
        floats = [f1, f2, f3]
        d, compr = self.serializer.serializeData(floats)
        v = self.serializer.deserializeData(d, compr)
        self.assertEqual(floats, v, "float precision must not be compromised in any serializer")

    def testSourceByteTypes_deserialize(self):
        # uncompressed
        call_ser, _ = self.serializer.serializeCall("object", "method", [1, 2, 3], {"kwarg": 42}, False)
        ser, _ = self.serializer.serializeData([4, 5, 6], False)
        _, _, vargs, _ = self.serializer.deserializeCall(bytearray(call_ser), False)
        self.assertEqual([1, 2, 3], vargs)
        d = self.serializer.deserializeData(bytearray(ser), False)
        self.assertEqual([4, 5, 6], d)
        if sys.version_info < (3, 0):
            _, _, vargs, _ = self.serializer.deserializeCall(buffer(call_ser), False)
            self.assertEqual([1, 2, 3], vargs)
            d = self.serializer.deserializeData(buffer(ser), False)
            self.assertEqual([4, 5, 6], d)
        # compressed
        call_ser, _ = self.serializer.serializeCall("object", "method", [1, 2, 3] * 100, {"kwarg": 42}, True)
        ser, _ = self.serializer.serializeData([4, 5, 6] * 100, True)
        _, _, vargs, _ = self.serializer.deserializeCall(bytearray(call_ser), True)
        self.assertEqual(300, len(vargs))
        d = self.serializer.deserializeData(bytearray(ser), True)
        self.assertEqual(300, len(d))
        if sys.version_info < (3, 0):
            _, _, vargs, _ = self.serializer.deserializeCall(buffer(call_ser), True)
            self.assertEqual(300, len(vargs))
            d = self.serializer.deserializeData(buffer(ser), True)
            self.assertEqual(300, len(d))

    @unittest.skipIf(sys.platform == "cli", "ironpython can't properly create memoryviews from serialized data")
    def testSourceByteTypes_deserialize_memoryview(self):
        # uncompressed
        call_ser, _ = self.serializer.serializeCall("object", "method", [1, 2, 3], {"kwarg": 42}, False)
        ser, _ = self.serializer.serializeData([4, 5, 6], False)
        _, _, vargs, _ = self.serializer.deserializeCall(memoryview(call_ser), False)
        self.assertEqual([1, 2, 3], vargs)
        d = self.serializer.deserializeData(memoryview(ser), False)
        self.assertEqual([4, 5, 6], d)
        # compressed
        call_ser, _ = self.serializer.serializeCall("object", "method", [1, 2, 3] * 100, {"kwarg": 42}, True)
        ser, _ = self.serializer.serializeData([4, 5, 6] * 100, True)
        _, _, vargs, _ = self.serializer.deserializeCall(memoryview(call_ser), True)
        self.assertEqual(300, len(vargs))
        d = self.serializer.deserializeData(memoryview(ser), True)
        self.assertEqual(300, len(d))

    def testSourceByteTypes_loads(self):
        call_ser, _ = self.serializer.serializeCall("object", "method", [1, 2, 3], {"kwarg": 42}, False)
        ser, _ = self.serializer.serializeData([4, 5, 6], False)
        _, _, vargs, _ = self.serializer.loadsCall(bytearray(call_ser))
        self.assertEqual([1, 2, 3], vargs)
        d = self.serializer.loads(bytearray(ser))
        self.assertEqual([4, 5, 6], d)
        if sys.version_info < (3, 0):
            _, _, vargs, _ = self.serializer.loadsCall(buffer(call_ser))
            self.assertEqual([1, 2, 3], vargs)
            d = self.serializer.loads(buffer(ser))
            self.assertEqual([4, 5, 6], d)

    @unittest.skipIf(sys.platform == "cli", "ironpython can't properly create memoryviews from serialized data")
    def testSourceByteTypes_loads_memoryview(self):
        call_ser, _ = self.serializer.serializeCall("object", "method", [1, 2, 3], {"kwarg": 42}, False)
        ser, _ = self.serializer.serializeData([4, 5, 6], False)
        _, _, vargs, _ = self.serializer.loadsCall(memoryview(call_ser))
        self.assertEqual([1, 2, 3], vargs)
        d = self.serializer.loads(memoryview(ser))
        self.assertEqual([4, 5, 6], d)

    def testSerializeDumpsAndDumpsCall(self):
        self.serializer.dumps(uuid.uuid4())
        self.serializer.dumps(Pyro4.URI("PYRO:test@test:4444"))
        self.serializer.dumps(Pyro4.Proxy("PYRONAME:foobar"))
        self.serializer.dumpsCall("obj", "method", (1, 2, 3), {"arg1": 999})
        self.serializer.dumpsCall("obj", "method", (1, 2, array.array('i', [1, 2, 3])), {"arg1": 999})
        self.serializer.dumpsCall("obj", "method", (1, 2, array.array('i', [1, 2, 3])), {"arg1": array.array('i', [1, 2, 3])})
        self.serializer.dumpsCall("obj", "method", (1, 2, Pyro4.URI("PYRO:test@test:4444")), {"arg1": 999})
        self.serializer.dumpsCall("obj", "method", (1, 2, Pyro4.URI("PYRO:test@test:4444")), {"arg1": Pyro4.URI("PYRO:test@test:4444")})
        self.serializer.dumpsCall("obj", "method", (1, 2, Pyro4.Proxy("PYRONAME:foobar")), {"arg1": 999})
        self.serializer.dumpsCall("obj", "method", (1, 2, Pyro4.Proxy("PYRONAME:foobar")), {"arg1": Pyro4.Proxy("PYRONAME:foobar")})

    def testArrays(self):
        if sys.version_info < (3, 0):
            a1 = array.array('c', b"hello")
            ser = self.serializer.dumps(a1)
            a2 = self.serializer.loads(ser)
            if type(a2) is array.array:
                self.assertEqual(a1, a2)
            else:
                self.assertEqual(b"hello", a2)
        a1 = array.array('u', unicode("hello"))
        ser = self.serializer.dumps(a1)
        a2 = self.serializer.loads(ser)
        if type(a2) is array.array:
            self.assertEqual(a1, a2)
        else:
            self.assertEqual(unicode("hello"), a2)
        a1 = array.array('h', [222, 333, 444, 555])
        ser = self.serializer.dumps(a1)
        a2 = self.serializer.loads(ser)
        if type(a2) is array.array:
            self.assertEqual(a1, a2)
        else:
            self.assertEqual([222, 333, 444, 555], a2)

    def testArrays2(self):
        if sys.version_info < (3, 0):
            a1 = array.array('c', b"hello")
            ser = self.serializer.dumpsCall("obj", "method", [a1], {})
            a2 = self.serializer.loads(ser)
            a2 = a2["params"][0] if self.SERIALIZER == "json" else a2[2][0]
            if type(a2) is array.array:
                self.assertEqual(a1, a2)
            else:
                self.assertEqual(b"hello", a2)
        a1 = array.array('u', unicode("hello"))
        ser = self.serializer.dumpsCall("obj", "method", [a1], {})
        a2 = self.serializer.loads(ser)
        a2 = a2["params"][0] if self.SERIALIZER == "json" else a2[2][0]
        if type(a2) is array.array:
            self.assertEqual(a1, a2)
        else:
            self.assertEqual(unicode("hello"), a2)
        a1 = array.array('h', [222, 333, 444, 555])
        ser = self.serializer.dumpsCall("obj", "method", [a1], {})
        a2 = self.serializer.loads(ser)
        a2 = a2["params"][0] if self.SERIALIZER == "json" else a2[2][0]
        if type(a2) is array.array:
            self.assertEqual(a1, a2)
        else:
            self.assertEqual([222, 333, 444, 555], a2)


class SerializeTests_cloudpickle(SerializeTests_pickle):
    SERIALIZER = "cloudpickle"

    @unittest.skip('not implemented')
    def testUriSerializationWithoutSlots(self):
        pass

    def testSerializeLambda(self):
        l = lambda x: x * x
        ser, compressed = self.serializer.serializeData(l)
        l2 = self.serializer.deserializeData(ser, compressed=compressed)
        self.assertEqual(l2(3.), 9.)

    def testSerializeLocalFunction(self):
        def f(x):
            return x * x
        ser, compressed = self.serializer.serializeData(f)
        f2 = self.serializer.deserializeData(ser, compressed=compressed)
        self.assertEqual(f2(3.), 9.)


is_ironpython_without_dill = False
try:
    import dill
except ImportError:
    if sys.platform == "cli":
        is_ironpython_without_dill = True


@unittest.skipIf(is_ironpython_without_dill, "dill with ironpython has issues so it's fine if we don't test this")
class SerializeTests_dill(SerializeTests_pickle):
    SERIALIZER = "dill"

    def testProtocolVersion(self):
        import dill
        self.assertEqual(dill.HIGHEST_PROTOCOL, config.DILL_PROTOCOL_VERSION)

    @unittest.skip('not implemented')
    def testUriSerializationWithoutSlots(self):
        pass

    def testSerializeLambda(self):
        l = lambda x: x * x
        ser, compressed = self.serializer.serializeData(l)
        l2 = self.serializer.deserializeData(ser, compressed=compressed)
        self.assertEqual(l2(3.), 9.)

    def testSerializeLocalFunction(self):
        def f(x):
            return x * x
        ser, compressed = self.serializer.serializeData(f)
        f2 = self.serializer.deserializeData(ser, compressed=compressed)
        self.assertEqual(f2(3.), 9.)


class SerializeTests_serpent(SerializeTests_pickle):
    SERIALIZER = "serpent"

    def testCircular(self):
        with self.assertRaises(ValueError):  # serpent doesn't support object graphs (since serpent 1.7 reports ValueError instead of crashing)
            super(SerializeTests_serpent, self).testCircular()

    def testSet(self):
        # serpent serializes a set into a tuple on older python versions, so we override this
        data = {111, 222, 333}
        ser, compressed = self.serializer.serializeData(data)
        data2 = self.serializer.deserializeData(ser, compressed=compressed)
        if serpent.can_use_set_literals:
            self.assertEqual(data, data2)
        else:
            self.assertEqual(tuple(data), data2)

    def testDeque(self):
        # serpent converts a deque into a primitive list
        deq = collections.deque([1, 2, 3, 4])
        ser, compressed = self.serializer.serializeData(deq)
        data2 = self.serializer.deserializeData(ser, compressed=compressed)
        self.assertEqual([1, 2, 3, 4], data2)

    @unittest.skipIf(sys.version_info < (2, 7), "ordereddict is in Python 2.7+")
    def testOrderedDict(self):
        od = collections.OrderedDict()
        od["a"] = 1
        od["b"] = 2
        od["c"] = 3
        def recreate_OrderedDict(name, values):
            self.assertEqual("collections.OrderedDict", name)
            return collections.OrderedDict(values["items"])
        Pyro4.util.SerializerBase.register_dict_to_class("collections.OrderedDict", recreate_OrderedDict)
        ser, compressed = self.serializer.serializeData(od)
        self.assertIn(b"collections.OrderedDict", ser)
        self.assertIn(b"[('a',1),('b',2),('c',3)]", ser)
        data2 = self.serializer.deserializeData(ser, compressed=compressed)
        self.assertEqual(od, data2)

    def testUriSerializationWithoutSlots(self):
        u = Pyro4.core.URI("PYRO:obj@localhost:1234")
        d, compr = self.serializer.serializeData(u)
        self.assertFalse(compr)
        result1 = b"# serpent utf-8 python3.2\n{'__class__':'Pyro4.core.URI','state':('PYRO','obj',None,'localhost',1234)}"
        result2 = b"# serpent utf-8 python3.2\n{'state':('PYRO','obj',None,'localhost',1234),'__class__':'Pyro4.core.URI'}"
        result3 = b"# serpent utf-8 python2.6\n{'state':('PYRO','obj',None,'localhost',1234),'__class__':'Pyro4.core.URI'}"
        result4 = b"# serpent utf-8 python2.6\n{'__class__':'Pyro4.core.URI','state':('PYRO','obj',None,'localhost',1234)}"
        self.assertTrue(d in (result1, result2, result3, result4))


class SerializeTests_json(SerializeTests_pickle):
    SERIALIZER = "json"

    def testCircular(self):
        with self.assertRaises(ValueError):  # json doesn't support object graphs
            super(SerializeTests_json, self).testCircular()

    def testSet(self):
        # json serializes a set into a list, so we override this
        data = {111, 222, 333}
        ser, compressed = self.serializer.serializeData(data)
        data2 = self.serializer.deserializeData(ser, compressed=compressed)
        self.assertEqual(list(data), data2)

    def testUriSerializationWithoutSlots(self):
        u = Pyro4.core.URI("PYRO:obj@localhost:1234")
        d, compr = self.serializer.serializeData(u)
        self.assertFalse(compr)
        result1 = b'{"__class__": "Pyro4.core.URI", "state": ["PYRO", "obj", null, "localhost", 1234]}'
        result2 = b'{"state": ["PYRO", "obj", null, "localhost", 1234], "__class__": "Pyro4.core.URI"}'
        self.assertTrue(d in (result1, result2))


class SerializeTests_marshal(SerializeTests_pickle):
    SERIALIZER = "marshal"

    def testCircular(self):
        with self.assertRaises(ValueError):  # marshal doesn't support object graphs
            super(SerializeTests_marshal, self).testCircular()

    @unittest.skip("marshaling is implementation dependent")
    def testUriSerializationWithoutSlots(self):
        pass


class SerializeTests_msgpack(SerializeTests_pickle):
    SERIALIZER = "msgpack"

    @unittest.skip("circular will crash msgpack")
    def testCircular(self):
        pass

    def testSet(self):
        # msgpack serializes a set into a list, so we override this
        data = {111, 222, 333}
        ser, compressed = self.serializer.serializeData(data)
        data2 = self.serializer.deserializeData(ser, compressed=compressed)
        self.assertEqual(list(data), data2)

    @unittest.skip("msgpack is implementation dependent")
    def testUriSerializationWithoutSlots(self):
        pass


class GenericTests(unittest.TestCase):
    def testSerializersAvailable(self):
        Pyro4.util.get_serializer("pickle")
        Pyro4.util.get_serializer("marshal")
        try:
            import json
            Pyro4.util.get_serializer("json")
        except ImportError:
            pass
        try:
            import serpent
            Pyro4.util.get_serializer("serpent")
        except ImportError:
            pass
        try:
            import cloudpickle
            Pyro4.util.get_serializer("cloudpickle")
        except ImportError:
            pass
        try:
            import dill
            Pyro4.util.get_serializer("dill")
        except ImportError:
            pass

    def testAssignedSerializerIds(self):
        self.assertEqual(1, Pyro4.util.SerpentSerializer.serializer_id)
        self.assertEqual(2, Pyro4.util.JsonSerializer.serializer_id)
        self.assertEqual(3, Pyro4.util.MarshalSerializer.serializer_id)
        self.assertEqual(4, Pyro4.util.PickleSerializer.serializer_id)
        self.assertEqual(5, Pyro4.util.DillSerializer.serializer_id)
        self.assertEqual(6, Pyro4.util.MsgpackSerializer.serializer_id)
        self.assertEqual(7, Pyro4.util.CloudpickleSerializer.serializer_id)

    def testSerializersAvailableById(self):
        Pyro4.util.get_serializer_by_id(1)  # serpent
        Pyro4.util.get_serializer_by_id(2)  # json
        Pyro4.util.get_serializer_by_id(3)  # marshal
        Pyro4.util.get_serializer_by_id(4)  # pickle
        # ids 5, 6 and 7 (dill, msgpack, cloudpickle) are not always available, so we skip those.
        self.assertRaises(Pyro4.errors.SerializeError, lambda: Pyro4.util.get_serializer_by_id(0))
        self.assertRaises(Pyro4.errors.SerializeError, lambda: Pyro4.util.get_serializer_by_id(8))

    def testDictClassFail(self):
        o = pprint.PrettyPrinter(stream="dummy", width=42)
        d = Pyro4.util.SerializerBase.class_to_dict(o)
        self.assertEqual(42, d["_width"])
        self.assertEqual("pprint.PrettyPrinter", d["__class__"])
        try:
            _ = Pyro4.util.SerializerBase.dict_to_class(d)
            self.fail("error expected")
        except Pyro4.errors.ProtocolError:
            pass

    def testDictException(self):
        x = ZeroDivisionError("hello", 42)
        expected = {
            "__class__": None,
            "__exception__": True,
            "args": ("hello", 42),
            "attributes": {}
        }
        if sys.version_info < (3, 0):
            expected["__class__"] = "exceptions.ZeroDivisionError"
        else:
            expected["__class__"] = "builtins.ZeroDivisionError"
        d = Pyro4.util.SerializerBase.class_to_dict(x)
        self.assertEqual(expected, d)
        x.custom_attribute = 999
        expected["attributes"] = {"custom_attribute": 999}
        d = Pyro4.util.SerializerBase.class_to_dict(x)
        self.assertEqual(expected, d)

    def testDictClassOk(self):
        uri = Pyro4.core.URI("PYRO:object@host:4444")
        d = Pyro4.util.SerializerBase.class_to_dict(uri)
        self.assertEqual("Pyro4.core.URI", d["__class__"])
        self.assertIn("state", d)
        x = Pyro4.util.SerializerBase.dict_to_class(d)
        self.assertIsInstance(x, Pyro4.core.URI)
        self.assertEqual(uri, x)
        self.assertEqual(4444, x.port)
        uri = Pyro4.core.URI("PYRO:12345@./u:/tmp/socketname")
        d = Pyro4.util.SerializerBase.class_to_dict(uri)
        self.assertEqual("Pyro4.core.URI", d["__class__"])
        self.assertIn("state", d)
        x = Pyro4.util.SerializerBase.dict_to_class(d)
        self.assertIsInstance(x, Pyro4.core.URI)
        self.assertEqual(uri, x)
        self.assertEqual("/tmp/socketname", x.sockname)

    def testCustomDictClass(self):
        o = MyThingPartlyExposed("test")
        Pyro4.util.SerializerBase.register_class_to_dict(MyThingPartlyExposed, mything_dict)
        Pyro4.util.SerializerBase.register_dict_to_class("CUSTOM-Mythingymabob", mything_creator)
        d = Pyro4.util.SerializerBase.class_to_dict(o)
        self.assertEqual("CUSTOM-Mythingymabob", d["__class__"])
        self.assertEqual("test", d["name"])
        x = Pyro4.util.SerializerBase.dict_to_class(d)
        self.assertIsInstance(x, MyThingPartlyExposed)
        self.assertEqual("test", x.name)
        # unregister the conversion functions and try again
        Pyro4.util.SerializerBase.unregister_class_to_dict(MyThingPartlyExposed)
        Pyro4.util.SerializerBase.unregister_dict_to_class("CUSTOM-Mythingymabob")
        d_orig = Pyro4.util.SerializerBase.class_to_dict(o)
        clsname = d_orig["__class__"]
        self.assertTrue(clsname.endswith("testsupport.MyThingPartlyExposed"))
        try:
            _ = Pyro4.util.SerializerBase.dict_to_class(d)
            self.fail("should crash")
        except Pyro4.errors.ProtocolError:
            pass  # ok

    def testExceptionNamespacePy2(self):
        data = {'__class__': 'exceptions.ZeroDivisionError',
                '__exception__': True,
                'args': ('hello', 42),
                'attributes': {"test_attribute": 99}}
        exc = Pyro4.util.SerializerBase.dict_to_class(data)
        self.assertIsInstance(exc, ZeroDivisionError)
        self.assertEqual("ZeroDivisionError('hello', 42)", repr(exc))
        self.assertEqual(99, exc.test_attribute)

    def testExceptionNamespacePy3(self):
        data = {'__class__': 'builtins.ZeroDivisionError',
                '__exception__': True,
                'args': ('hello', 42),
                'attributes': {"test_attribute": 99}}
        exc = Pyro4.util.SerializerBase.dict_to_class(data)
        self.assertIsInstance(exc, ZeroDivisionError)
        self.assertEqual("ZeroDivisionError('hello', 42)", repr(exc))
        self.assertEqual(99, exc.test_attribute)

    def testExceptionNotTagged(self):
        data = {'__class__': 'builtins.ZeroDivisionError',
                'args': ('hello', 42),
                'attributes': {}}
        with self.assertRaises(Pyro4.errors.SerializeError) as cm:
            _ = Pyro4.util.SerializerBase.dict_to_class(data)
        self.assertEqual("unsupported serialized class: builtins.ZeroDivisionError", str(cm.exception))

    def testWeirdFloats(self):
        ser = Pyro4.util.get_serializer(config.SERIALIZER)
        p, _ = ser.serializeData([float("+inf"), float("-inf"), float("nan")])
        s2 = ser.deserializeData(p)
        self.assertTrue(math.isinf(s2[0]))
        self.assertEqual(1.0, math.copysign(1, s2[0]))
        self.assertTrue(math.isinf(s2[1]))
        self.assertEqual(-1.0, math.copysign(1, s2[1]))
        self.assertTrue(math.isnan(s2[2]))


def mything_dict(obj):
    return {
        "__class__": "CUSTOM-Mythingymabob",
        "name": obj.name
    }


def mything_creator(classname, d):
    assert classname == "CUSTOM-Mythingymabob"
    assert d["__class__"] == "CUSTOM-Mythingymabob"
    return MyThingPartlyExposed(d["name"])


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
