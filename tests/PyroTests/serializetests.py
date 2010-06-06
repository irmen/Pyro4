"""
Tests for the data serializer.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong.
irmen@razorvine.net - http://www.razorvine.net/python/Pyro
"""

import unittest, sys, os
import Pyro.util
import Pyro.errors
import Pyro.core

class SerializeTests(unittest.TestCase):
    
    def setUp(self):
        self.ser=Pyro.util.Serializer()
        
    def testSerItself(self):
        s=Pyro.util.Serializer()
        p,_=self.ser.serialize(s)
        s2=self.ser.deserialize(p)
        self.assertEqual(s,s2)

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
        e1=Pyro.errors.NamingError("x")
        e2=Pyro.errors.PyroError("x")
        e3=Pyro.errors.ProtocolError("x")
        p,_=self.ser.serialize(e1)
        e=self.ser.deserialize(p)
        self.assertTrue(isinstance(e, Pyro.errors.NamingError))
        self.assertEqual(repr(e1), repr(e))
        p,_=self.ser.serialize(e2)
        e=self.ser.deserialize(p)
        self.assertTrue(isinstance(e, Pyro.errors.PyroError))
        self.assertEqual(repr(e2), repr(e))
        p,_=self.ser.serialize(e3)
        e=self.ser.deserialize(p)
        self.assertTrue(isinstance(e, Pyro.errors.ProtocolError))
        self.assertEqual(repr(e3), repr(e))
    
    def testSerCoreOffline(self):
        uri=Pyro.core.URI("PYRO:9999@host.com:4444")
        p,_=self.ser.serialize(uri)
        uri2=self.ser.deserialize(p)
        self.assertEqual(uri, uri2)
        self.assertEqual("PYRO",uri2.protocol)
        self.assertEqual("9999",uri2.object)
        self.assertEqual("host.com:4444",uri2.location)
        proxy=Pyro.core.Proxy("PYRO:9999@host.com:4444")
        proxy._pyroTimeout=42
        self.assertTrue(proxy._pyroConnection is None)
        p,_=self.ser.serialize(proxy)
        proxy2=self.ser.deserialize(p)
        self.assertTrue(proxy._pyroConnection is None)
        self.assertTrue(proxy2._pyroConnection is None)
        self.assertEqual(proxy2._pyroUri, proxy._pyroUri)
        self.assertEqual(proxy2._pyroSerializer, proxy._pyroSerializer)
        self.assertEqual(42, proxy2._pyroTimeout)
        
    def testSerVersion(self):
        if os.name=="java":
            return # jython cannot run this testcase...
        data="data"
        p,_=self.ser.serialize(data)
        r=self.ser.deserialize(p)
        self.assertEqual(data,r)
        orig_hexversion=sys.hexversion
        orig_versioninfo=sys.version_info
        try:
            # set some silly versions to force a communicationerror
            sys.hexversion=0x999955f0   
            sys.version_info=(199,199,199,"bogus",0)
            p,_=self.ser.serialize("data")
        finally:
            sys.hexversion=orig_hexversion
            sys.version_info=orig_versioninfo
        self.assertRaises(Pyro.errors.CommunicationError, self.ser.deserialize, p)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
