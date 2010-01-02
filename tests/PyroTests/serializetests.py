import unittest
import socket
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

    def _assertNameServerRunning(self):
        try:
            self.ns=Pyro.naming.locateNS()
        except Pyro.errors.PyroError:
            print "Can't find a name server"
            self.fail("No name server found. You need to have a name server running (+broadcast server) to be able to run this tests")

    def testSerCoreOnline(self):
        self._assertNameServerRunning()
        # online serialization tests
        ser=Pyro.util.Serializer()
        nsLocation="%s:%d" %(self.ns._pyroUri.host, self.ns._pyroUri.port)
        daemonUri="PYROLOC:"+Pyro.constants.DAEMON_LOCALNAME+"@"+nsLocation
        proxy=Pyro.core.Proxy(daemonUri)
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
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
