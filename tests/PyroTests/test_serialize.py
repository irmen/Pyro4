"""
Tests for the data serializer.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import unittest
import Pyro4.util
import Pyro4.errors
import Pyro4.core
from testsupport import *


class Something(object):
    pass


class SerializeTests(unittest.TestCase):
    
    def setUp(self):
        Pyro4.config.HMAC_KEY=tobytes("testsuite")
        self.ser=Pyro4.util.serializers["pickle"]
    def tearDown(self):
        Pyro4.config.HMAC_KEY=None
        
    def testSerItself(self):
        s=Pyro4.util.serializers["pickle"]
        p,_=self.ser.serializeData(s)
        s2=self.ser.deserializeData(p)
        self.assertEqual(s,s2)
        self.assertTrue(s==s2)
        self.assertFalse(s!=s2)

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
        e1=Pyro4.errors.NamingError("x")
        e2=Pyro4.errors.PyroError("x")
        e3=Pyro4.errors.ProtocolError("x")
        p,_=self.ser.serializeData(e1)
        e=self.ser.deserializeData(p)
        self.assertTrue(isinstance(e, Pyro4.errors.NamingError))
        self.assertEqual(repr(e1), repr(e))
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
        proxy=Pyro4.core.Proxy("PYRO:9999@host.com:4444")
        proxy._pyroTimeout=42
        self.assertTrue(proxy._pyroConnection is None)
        p,_=self.ser.serializeData(proxy)
        proxy2=self.ser.deserializeData(p)
        self.assertTrue(proxy._pyroConnection is None)
        self.assertTrue(proxy2._pyroConnection is None)
        self.assertEqual(proxy2._pyroUri, proxy._pyroUri)
        self.assertEqual(proxy2._pyroSerializer, proxy._pyroSerializer)
        self.assertEqual(42, proxy2._pyroTimeout)

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
                obj=Something()
                obj.name="hello"
                daemon.register(obj)
                o,_=self.ser.serializeData(obj)
                o2=self.ser.deserializeData(o)
                self.assertEqual("hello", o2.name)
            finally:
                Pyro4.config.AUTOPROXY=True

    def testSerializeException(self):
        e = ZeroDivisionError("hello")
        d = self.ser.serializeException(e)
        e2 = self.ser.makeException(self.ser.deserializeData(d))
        self.assertIsInstance(e2, ZeroDivisionError)
        self.assertEqual("hello", str(e2))


class SerializersTests(unittest.TestCase):
    serializernames = ["pickle", "marshal", "json", "xmlrpc", "serpent"]

    def testMinimalSerializers(self):
        self.assertTrue("pickle" in Pyro4.util.serializers)
        self.assertTrue("marshal" in Pyro4.util.serializers)
        try:
            import json
            self.assertTrue("json" in Pyro4.util.serializers)
        except ImportError:
            pass
        try:
            import serpent
            self.assertTrue("serpent" in Pyro4.util.serializers)
        except ImportError:
            pass


    def testData(self):
        for name in self.serializernames:
            if name not in Pyro4.util.serializers:
                continue
            serializer = Pyro4.util.serializers[name]
            data = [42, "hello"]
            ser, compressed = serializer.serializeData(data)
            self.assertFalse(compressed)
            data2 = serializer.deserializeData(ser, compressed=False)
            self.assertEqual(data, data2)

    def testCall(self):
        for name in self.serializernames:
            if name not in Pyro4.util.serializers:
                continue
            serializer = Pyro4.util.serializers[name]
            ser, compressed = serializer.serializeCall("object", "method", "vargs", "kwargs")
            self.assertFalse(compressed)
            obj, method, vargs, kwargs = serializer.deserializeCall(ser, compressed=False)
            self.assertEqual("object", obj)
            self.assertEqual("method", method)
            self.assertEqual("vargs", vargs)
            self.assertEqual("kwargs", kwargs)

    def testException(self):
        e = ZeroDivisionError("hello")
        for name in self.serializernames:
            if name not in Pyro4.util.serializers:
                continue
            serializer = Pyro4.util.serializers[name]
            ser = serializer.serializeException(e)
            e2 = serializer.deserializeData(ser)
            e2 = serializer.makeException(e2)
            self.assertIsInstance(e2, ZeroDivisionError)
            self.assertEqual("hello", str(e2))


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
