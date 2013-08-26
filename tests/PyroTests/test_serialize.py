"""
Tests for the data serializer.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import sys
import os
import copy
import pprint
import Pyro4.util
import Pyro4.errors
import Pyro4.core
import Pyro4.futures
import Pyro4.message
from testsupport import *


class SerializeTests_pickle(unittest.TestCase):
    SERIALIZER="pickle"
    def setUp(self):
        self.previous_serializer=Pyro4.config.SERIALIZER
        Pyro4.config.SERIALIZER=self.SERIALIZER
        Pyro4.config.HMAC_KEY=b"testsuite"
        self.ser=Pyro4.util.get_serializer(Pyro4.config.SERIALIZER)
    def tearDown(self):
        Pyro4.config.HMAC_KEY=None
        Pyro4.config.SERIALIZER=self.previous_serializer
        
    def testSerItself(self):
        s=Pyro4.util.get_serializer(Pyro4.config.SERIALIZER)
        p,_=self.ser.serializeData(s)
        s2=self.ser.deserializeData(p)
        self.assertEqual(s,s2)
        self.assertTrue(s==s2)
        self.assertFalse(s!=s2)

    def testSerUnicode(self):
        data = unicode("x")
        ser,_ = self.ser.serializeData(data)
        expected_type = str if sys.platform=="cli" else bytes   # ironpython serializes into str, not bytes... :(
        self.assertTrue(type(ser) is expected_type)
        ser,_ = self.ser.serializeCall(data, unicode("method"), [], {})
        self.assertTrue(type(ser) is expected_type)

    def testSerCompression(self):
        d1,c1=self.ser.serializeData("small data", compress=True)
        d2,c2=self.ser.serializeData("small data", compress=False)
        self.assertFalse(c1)
        self.assertEqual(d1,d2)
        bigdata="x"*1000
        d1,c1=self.ser.serializeData(bigdata, compress=False)
        d2,c2=self.ser.serializeData(bigdata, compress=True)
        self.assertFalse(c1)
        self.assertTrue(c2)
        self.assertTrue(len(d2) < len(d1))
        self.assertEqual(bigdata, self.ser.deserializeData(d1, compressed=False))
        self.assertEqual(bigdata, self.ser.deserializeData(d2, compressed=True))

    def testSerErrors(self):
        e1=Pyro4.errors.NamingError(unicode("x"))
        e1._pyroTraceback = ["this is the remote traceback"]
        orig_e = copy.copy(e1)
        e2=Pyro4.errors.PyroError(unicode("x"))
        e3=Pyro4.errors.ProtocolError(unicode("x"))
        if sys.platform=="cli":
            Pyro4.util.fixIronPythonExceptionForPickle(e1, True)
        p,_=self.ser.serializeData(e1)
        e=self.ser.deserializeData(p)
        if sys.platform=="cli":
            Pyro4.util.fixIronPythonExceptionForPickle(e, False)
        self.assertTrue(isinstance(e, Pyro4.errors.NamingError))
        self.assertEqual(repr(orig_e), repr(e))
        self.assertEqual(["this is the remote traceback"], e._pyroTraceback, "remote traceback info should be present")
        p,_=self.ser.serializeData(e2)
        e=self.ser.deserializeData(p)
        self.assertTrue(isinstance(e, Pyro4.errors.PyroError))
        self.assertEqual(repr(e2), repr(e))
        p,_=self.ser.serializeData(e3)
        e=self.ser.deserializeData(p)
        self.assertTrue(isinstance(e, Pyro4.errors.ProtocolError))
        self.assertEqual(repr(e3), repr(e))
    
    def testSerializeExceptionWithAttr(self):
        ex=ZeroDivisionError("test error")
        ex._pyroTraceback=["test traceback payload"]
        Pyro4.util.fixIronPythonExceptionForPickle(ex,True) # hack for ironpython
        data,compressed=self.ser.serializeData(ex)
        ex2=self.ser.deserializeData(data,compressed)
        Pyro4.util.fixIronPythonExceptionForPickle(ex2,False) # hack for ironpython
        self.assertEqual(ZeroDivisionError, type(ex2))
        self.assertTrue(hasattr(ex2, "_pyroTraceback"))
        self.assertEqual(["test traceback payload"], ex2._pyroTraceback)

    def testSerCoreOffline(self):
        uri=Pyro4.core.URI("PYRO:9999@host.com:4444")
        p,_=self.ser.serializeData(uri)
        uri2=self.ser.deserializeData(p)
        self.assertEqual(uri, uri2)
        self.assertEqual("PYRO",uri2.protocol)
        self.assertEqual("9999",uri2.object)
        self.assertEqual("host.com:4444",uri2.location)
        self.assertEqual(4444, uri2.port)
        self.assertEqual(None, uri2.sockname)

        uri=Pyro4.core.URI("PYRO:12345@./u:/tmp/socketname")
        p,_=self.ser.serializeData(uri)
        uri2=self.ser.deserializeData(p)
        self.assertEqual(uri, uri2)
        self.assertEqual("PYRO",uri2.protocol)
        self.assertEqual("12345",uri2.object)
        self.assertEqual("./u:/tmp/socketname",uri2.location)
        self.assertEqual(None, uri2.port)
        self.assertEqual("/tmp/socketname", uri2.sockname)

        proxy=Pyro4.core.Proxy("PYRO:9999@host.com:4444")
        proxy._pyroTimeout=42
        self.assertTrue(proxy._pyroConnection is None)
        p,_=self.ser.serializeData(proxy)
        proxy2=self.ser.deserializeData(p)
        self.assertTrue(proxy._pyroConnection is None)
        self.assertTrue(proxy2._pyroConnection is None)
        self.assertEqual(proxy2._pyroUri, proxy._pyroUri)
        self.assertEqual(42, proxy2._pyroTimeout)

    def testNested(self):
        if self.SERIALIZER=="marshal":
            self.skipTest("marshal can't serialize custom objects")
        uri1=Pyro4.core.URI("PYRO:1111@host.com:111")
        uri2=Pyro4.core.URI("PYRO:2222@host.com:222")
        _=self.ser.serializeData(uri1)
        data=[uri1, uri2]
        p,_=self.ser.serializeData(data)
        [u1, u2]=self.ser.deserializeData(p)
        self.assertEqual(uri1, u1)
        self.assertEqual(uri2, u2)

    def testSerDaemonHack(self):
        # This tests the hack that a Daemon should be serializable,
        # but only to support serializing Pyro objects.
        # The serialized form of a Daemon should be empty (and thus, useless)
        with Pyro4.core.Daemon(port=0) as daemon:
            d,_=self.ser.serializeData(daemon)
            d2=self.ser.deserializeData(d)
            self.assertTrue(len(d2.__dict__)==0, "deserialized daemon should be empty")
            try:
                Pyro4.config.AUTOPROXY=False
                obj=pprint.PrettyPrinter(stream="dummy", width=42)
                obj.name="hello"
                daemon.register(obj)
                o,_=self.ser.serializeData(obj)
                if self.SERIALIZER=="pickle":
                    # only pickle can deserialize the PrettyPrinter class without the need of explicit deserialization function
                    o2=self.ser.deserializeData(o)
                    self.assertEqual("hello", o2.name)
                    self.assertEqual(42, o2._width)
            finally:
                Pyro4.config.AUTOPROXY=True

    def testPyroClasses(self):
        uri = Pyro4.core.URI("PYRO:object@host:4444")
        s, c = self.ser.serializeData(uri)
        x = self.ser.deserializeData(s, c)
        self.assertEqual(uri, x)
        uri=Pyro4.core.URI("PYRO:12345@./u:/tmp/socketname")
        s, c = self.ser.serializeData(uri)
        x = self.ser.deserializeData(s, c)
        self.assertEqual(uri, x)
        proxy=Pyro4.core.Proxy(uri)
        s, c = self.ser.serializeData(proxy)
        x = self.ser.deserializeData(s, c)
        self.assertEqual(proxy._pyroUri, x._pyroUri)
        self.assertTrue(x._)
        daemon=Pyro4.core.Daemon()
        s, c = self.ser.serializeData(daemon)
        x = self.ser.deserializeData(s, c)
        self.assertTrue(isinstance(x, Pyro4.core.Daemon))
        wrapper = Pyro4.futures._ExceptionWrapper(ZeroDivisionError("divided by zero"))
        s, c = self.ser.serializeData(wrapper)
        x = self.ser.deserializeData(s, c)
        self.assertIsInstance(x, Pyro4.futures._ExceptionWrapper)
        self.assertEqual("divided by zero", str(x.exception))

    def testAutoProxy(self):
        if self.SERIALIZER=="marshal":
            self.skipTest("marshal can't serialize custom objects")
        self.ser.register_type_replacement(MyThing2, Pyro4.core.pyroObjectToAutoProxy)
        t1 = MyThing2("1")
        t2 = MyThing2("2")
        with Pyro4.core.Daemon() as d:
            d.register(t1, "thingy1")
            d.register(t2, "thingy2")
            data = [t1, ["apple", t2] ]
            s, c = self.ser.serializeData(data)
            data = self.ser.deserializeData(s, c)
            self.assertEqual("apple", data[1][0])
            p1 = data[0]
            p2 = data[1][1]
            self.assertIsInstance(p1, Pyro4.core.Proxy)
            self.assertIsInstance(p2, Pyro4.core.Proxy)
            self.assertEqual("thingy1", p1._pyroUri.object)
            self.assertEqual("thingy2", p2._pyroUri.object)

    def testCustomClassFail(self):
        if self.SERIALIZER=="pickle":
            self.skipTest("pickle simply serializes custom classes")
        o = pprint.PrettyPrinter(stream="dummy", width=42)
        s, c = self.ser.serializeData(o)
        try:
            x = self.ser.deserializeData(s, c)
            self.fail("error expected, shouldn't deserialize unknown class")
        except Pyro4.errors.ProtocolError:
            pass

    def testData(self):
        data = [42, "hello"]
        ser, compressed = self.ser.serializeData(data)
        expected_type = str if sys.platform=="cli" else bytes   # ironpython serializes into str, not bytes... :(
        self.assertTrue(type(ser) is expected_type)
        self.assertFalse(compressed)
        data2 = self.ser.deserializeData(ser, compressed=False)
        self.assertEqual(data, data2)

    def testCallPlain(self):
        ser, compressed = self.ser.serializeCall("object", "method", "vargs", "kwargs")
        self.assertFalse(compressed)
        obj, method, vargs, kwargs = self.ser.deserializeCall(ser, compressed=False)
        self.assertEqual("object", obj)
        self.assertEqual("method", method)
        self.assertEqual("vargs", vargs)
        self.assertEqual("kwargs", kwargs)

    def testCallPyroObjAsArg(self):
        if self.SERIALIZER=="marshal":
            self.skipTest("marshal can't serialize custom objects")
        uri = Pyro4.core.URI("PYRO:555@localhost:80")
        ser, compressed = self.ser.serializeCall("object", "method", [uri], {"thing": uri})
        self.assertFalse(compressed)
        obj, method, vargs, kwargs = self.ser.deserializeCall(ser, compressed=False)
        self.assertEqual("object", obj)
        self.assertEqual("method", method)
        self.assertEqual([uri], vargs)
        self.assertEqual({"thing": uri}, kwargs)

    def testCallCustomObjAsArg(self):
        if self.SERIALIZER=="marshal":
            self.skipTest("marshal can't serialize custom objects")
        e = ZeroDivisionError("hello")
        ser, compressed = self.ser.serializeCall("object", "method", [e], {"thing": e})
        self.assertFalse(compressed)
        obj, method, vargs, kwargs = self.ser.deserializeCall(ser, compressed=False)
        self.assertEqual("object", obj)
        self.assertEqual("method", method)
        self.assertTrue(isinstance(vargs, list))
        self.assertTrue(isinstance(vargs[0], ZeroDivisionError))
        self.assertEqual("hello", str(vargs[0]))
        self.assertTrue(isinstance(kwargs["thing"], ZeroDivisionError))
        self.assertEqual("hello", str(kwargs["thing"]))

    def testSerializeException(self):
        e = ZeroDivisionError()
        d, c = self.ser.serializeData(e)
        e2 = self.ser.deserializeData(d, c)
        self.assertTrue(isinstance(e2, ZeroDivisionError))
        self.assertEqual("", str(e2))
        e = ZeroDivisionError("hello")
        d, c = self.ser.serializeData(e)
        e2 = self.ser.deserializeData(d, c)
        self.assertTrue(isinstance(e2, ZeroDivisionError))
        self.assertEqual("hello", str(e2))
        e = ZeroDivisionError("hello", 42)
        d, c = self.ser.serializeData(e)
        e2 = self.ser.deserializeData(d, c)
        self.assertTrue(isinstance(e2, ZeroDivisionError))
        self.assertTrue(str(e2) in ("('hello', 42)", "(u'hello', 42)"))
        e.custom_attribute = 999
        if sys.platform=="cli":
            Pyro4.util.fixIronPythonExceptionForPickle(e, True)
        ser, compressed = self.ser.serializeData(e)
        e2 = self.ser.deserializeData(ser, compressed)
        if sys.platform=="cli":
            Pyro4.util.fixIronPythonExceptionForPickle(e2, False)
        self.assertTrue(isinstance(e2, ZeroDivisionError))
        self.assertTrue(str(e2) in ("('hello', 42)", "(u'hello', 42)"))
        self.assertEqual(999, e2.custom_attribute)

    def testSerializeSpecialException(self):
        self.assertTrue("GeneratorExit" in Pyro4.util.all_exceptions)
        e = GeneratorExit()
        d, c = self.ser.serializeData(e)
        e2 = self.ser.deserializeData(d, c)
        self.assertTrue(isinstance(e2, GeneratorExit))

    def testRecreateClasses(self):
        self.assertEqual([1,2,3], self.ser.recreate_classes([1,2,3]))
        d = {"__class__": "invalid" }
        try:
            self.ser.recreate_classes(d)
            self.fail("error expected")
        except Pyro4.errors.ProtocolError:
            pass  # ok
        d = {"__class__": "Pyro4.core.URI", "state": ['PYRO', '555', None, 'localhost', 80] }
        uri = self.ser.recreate_classes(d)
        self.assertEqual(Pyro4.core.URI("PYRO:555@localhost:80"), uri)
        number, uri = self.ser.recreate_classes([1,{"uri": d}])
        self.assertEqual(1, number)
        self.assertEqual(Pyro4.core.URI("PYRO:555@localhost:80"), uri["uri"])


class SerializeTests_serpent(SerializeTests_pickle):
    SERIALIZER="serpent"

class SerializeTests_json(SerializeTests_pickle):
    SERIALIZER="json"

if os.name!="java":
    # The marshal serializer is not working correctly under jython,
    # see http://bugs.jython.org/issue2077
    # So we only include this when not running jython
    class SerializeTests_marshal(SerializeTests_pickle):
        SERIALIZER="marshal"


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

    def testSerializersAvailableById(self):
        Pyro4.util.get_serializer_by_id(Pyro4.message.SERIALIZER_PICKLE)
        Pyro4.util.get_serializer_by_id(Pyro4.message.SERIALIZER_MARSHAL)
        self.assertRaises(Pyro4.errors.ProtocolError, lambda: Pyro4.util.get_serializer_by_id(9999999))

    def testDictClassFail(self):
        o = pprint.PrettyPrinter(stream="dummy", width=42)
        d = Pyro4.util.SerializerBase.class_to_dict(o)
        self.assertEqual(42, d["_width"])
        self.assertEqual("pprint.PrettyPrinter", d["__class__"])
        try:
            x = Pyro4.util.SerializerBase.dict_to_class(d)
            self.fail("error expected")
        except Pyro4.errors.ProtocolError:
            pass

    def testDictException(self):
        x = ZeroDivisionError("hello", 42)
        expected = {
            "__class__": None,
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
        self.assertTrue("state" in d)
        x = Pyro4.util.SerializerBase.dict_to_class(d)
        self.assertEqual(uri, x)
        self.assertEqual(4444, x.port)
        uri = Pyro4.core.URI("PYRO:12345@./u:/tmp/socketname")
        d = Pyro4.util.SerializerBase.class_to_dict(uri)
        self.assertEqual("Pyro4.core.URI", d["__class__"])
        self.assertTrue("state" in d)
        x = Pyro4.util.SerializerBase.dict_to_class(d)
        self.assertEqual(uri, x)
        self.assertEqual("/tmp/socketname", x.sockname)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
