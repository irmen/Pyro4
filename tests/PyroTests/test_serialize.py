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
        self.ser=Pyro4.util.Serializer()
    def tearDown(self):
        Pyro4.config.HMAC_KEY=None
        
    def testSerItself(self):
        s=Pyro4.util.Serializer()
        p,_=self.ser.serialize(s)
        s2=self.ser.deserialize(p)
        self.assertEqual(s,s2)
        self.assertTrue(s==s2)
        self.assertFalse(s!=s2)

    def testSerCompression(self):
        d1,c1=self.ser.serialize("small data", compress=True)
        d2,c2=self.ser.serialize("small data", compress=False)
        self.assertFalse(c1)
        self.assertEqual(d1,d2)
        bigdata="x"*1000
        d1,c1=self.ser.serialize(bigdata, compress=False)
        d2,c2=self.ser.serialize(bigdata, compress=True)
        self.assertFalse(c1)
        self.assertTrue(c2)
        self.assertTrue(len(d2) < len(d1))
        self.assertEqual(bigdata, self.ser.deserialize(d1, compressed=False))
        self.assertEqual(bigdata, self.ser.deserialize(d2, compressed=True))

    def testSerErrors(self):
        e1=Pyro4.errors.NamingError("x")
        e2=Pyro4.errors.PyroError("x")
        e3=Pyro4.errors.ProtocolError("x")
        p,_=self.ser.serialize(e1)
        e=self.ser.deserialize(p)
        self.assertTrue(isinstance(e, Pyro4.errors.NamingError))
        self.assertEqual(repr(e1), repr(e))
        p,_=self.ser.serialize(e2)
        e=self.ser.deserialize(p)
        self.assertTrue(isinstance(e, Pyro4.errors.PyroError))
        self.assertEqual(repr(e2), repr(e))
        p,_=self.ser.serialize(e3)
        e=self.ser.deserialize(p)
        self.assertTrue(isinstance(e, Pyro4.errors.ProtocolError))
        self.assertEqual(repr(e3), repr(e))
    
    def testSerializeExceptionWithAttr(self):
        ex=ZeroDivisionError("test error")
        ex._pyroTraceback=["test traceback payload"]
        Pyro4.core.fixIronPythonExceptionForPickle(ex,True) # hack for ironpython
        data,compressed=self.ser.serialize(ex)
        ex2=self.ser.deserialize(data,compressed)
        Pyro4.core.fixIronPythonExceptionForPickle(ex2,False) # hack for ironpython
        self.assertEqual(ZeroDivisionError, type(ex2))
        self.assertTrue(hasattr(ex2, "_pyroTraceback"))
        self.assertEqual(["test traceback payload"], ex2._pyroTraceback)

    def testSerCoreOffline(self):
        uri=Pyro4.core.URI("PYRO:9999@host.com:4444")
        p,_=self.ser.serialize(uri)
        uri2=self.ser.deserialize(p)
        self.assertEqual(uri, uri2)
        self.assertEqual("PYRO",uri2.protocol)
        self.assertEqual("9999",uri2.object)
        self.assertEqual("host.com:4444",uri2.location)
        proxy=Pyro4.core.Proxy("PYRO:9999@host.com:4444")
        proxy._pyroTimeout=42
        self.assertTrue(proxy._pyroConnection is None)
        p,_=self.ser.serialize(proxy)
        proxy2=self.ser.deserialize(p)
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
            d,_=self.ser.serialize(daemon)
            d2=self.ser.deserialize(d)
            self.assertTrue(len(d2.__dict__)==0, "deserialized daemon should be empty")
            try:
                Pyro4.config.AUTOPROXY=False
                obj=Something()
                obj.name="hello"
                daemon.register(obj)
                o,_=self.ser.serialize(obj)
                o2=self.ser.deserialize(o)
                self.assertEqual("hello", o2.name)
            finally:
                Pyro4.config.AUTOPROXY=True


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
