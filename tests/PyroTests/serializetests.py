import unittest
import Pyro.util
import Pyro.errors
import Pyro.core
import Pyro.naming

class SerializeTests(unittest.TestCase):
    
    def setUp(self):
        self.ser=Pyro.util.Serializer()
        
    def testSerMisc(self):
        s=Pyro.util.Serializer()
        p,_=self.ser.serialize(s)
        s2=self.ser.deserialize(p)
        self.assertEqual(s,s2)

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
        uri=Pyro.core.PyroURI("PYRO:9999@host.com:4444")
        p,_=self.ser.serialize(uri)
        uri2=self.ser.deserialize(p)
        self.assertEqual(uri, uri2)
        self.assertEqual("PYRO",uri2.protocol)
        self.assertEqual("9999",uri2.object)
        self.assertEqual("host.com:4444",uri2.location)
        proxy=Pyro.core.Proxy("PYRO:9999@host.com:4444")
        self.assertTrue(proxy._pyroConnection is None)
        p,_=self.ser.serialize(proxy)
        proxy2=self.ser.deserialize(p)
        self.assertTrue(proxy._pyroConnection is None)
        self.assertTrue(proxy2._pyroConnection is None)
        self.assertEqual(proxy2._pyroUri, proxy._pyroUri)
        self.assertEqual(proxy2._pyroSerializer, proxy._pyroSerializer)
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
