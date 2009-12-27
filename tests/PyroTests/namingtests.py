import unittest
import Pyro.naming
import Pyro.config

class NSLookupTests(unittest.TestCase):

    def setUp(self):
        #@todo: set up a name server
        pass

    def tearDown(self):
        #@todo: close down the name server
        pass

    def testLookup(self):
        self.assertRaises(NotImplementedError, Pyro.naming.NameServer.locate)
        ns=Pyro.naming.NameServer.locate("host.com")
        self.assertTrue(isinstance(ns, Pyro.core.Proxy))
        uri=ns._pyroUri
        self.assertEqual("PYRO",uri.protocol)
        self.assertEqual("host.com",uri.host)
        self.assertEqual(Pyro.config.DEFAULT_NS_PORT,uri.port)
        ns=Pyro.naming.NameServer.locate("host.com:9999")
        uri=ns._pyroUri
        self.assertEqual("PYRO",uri.protocol)
        self.assertEqual("host.com",uri.host)
        self.assertEqual(9999,uri.port)
        ns=Pyro.naming.NameServer.locate("./p:pipename")
        uri=ns._pyroUri
        self.assertEqual("PYRO",uri.protocol)
        self.assertEqual("pipename",uri.pipename)

    def testResolve(self):
        resolved1=Pyro.naming.resolve(Pyro.core.PyroURI("PYRO:12345@host.com"))
        resolved2=Pyro.naming.resolve("PYRO:12345@host.com")
        self.assertTrue(type(resolved1) is Pyro.core.PyroURI)
        self.assertEqual(resolved1, resolved2)
        uri=Pyro.naming.resolve("PYROLOC:objectname@host.com")
        self.assertEqual("PYRO",uri.protocol)
        self.assertEqual("host.com",uri.host)
        self.assertNotEqual("objectname",uri.object)
        uri=Pyro.naming.resolve("PYRONAME:objectname@host.com")
        self.assertEqual("PYRO",uri.protocol)
        self.assertEqual("host.com",uri.host)
        self.assertNotEqual("objectname",uri.object)
        self.assertRaises(NotImplementedError, Pyro.naming.resolve, "PYRONAME:objectname" )
        # test with wrong argument type
        self.assertRaises(TypeError, Pyro.naming.resolve, 999)

del NSLookupTests
print "NS TESTS DISABLED" #@todo: fix them 


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
