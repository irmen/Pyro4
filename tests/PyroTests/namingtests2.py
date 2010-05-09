import unittest
import Pyro.naming
from Pyro.errors import NamingError,PyroError

# offline name-server tests

class OfflineTests(unittest.TestCase):
    def testRegister(self):
        ns=Pyro.naming.NameServer()
        ns.ping()
        ns.register("test.object1","PYRO:111111@host.com:4444")
        ns.register("test.object2","PYRO:222222@host.com:4444")
        ns.register("test.object3","PYRO:333333@host.com:4444")
        ns.register("test.sub.objectA",Pyro.core.PyroURI("PYRO:AAAAAA@host.com:4444"))
        ns.register("test.sub.objectB",Pyro.core.PyroURI("PYRO:BBBBBB@host.com:4444"))
        
        self.assertRaises(NamingError, ns.lookup, "unknown_object")
        
        uri=ns.lookup("test.object3")
        self.assertEqual(Pyro.core.PyroURI("PYRO:333333@host.com:4444"), uri)   # lookup always returns PyroURI
        ns.remove("unknown_object")
        ns.remove("test.object1")
        ns.remove("test.object2")
        ns.remove("test.object3")
        all=ns.list()
        self.assertEqual(2, len(all))  # 2 leftover objects

        self.assertRaises(PyroError, ns.register, "test.nonurivalue", "THISVALUEISNOTANURI")

    def testList(self):
        ns=Pyro.naming.NameServer()
        ns.register("test.objects.1","PYRONAME:something1")
        ns.register("test.objects.2","PYRONAME:something2")
        ns.register("test.objects.3","PYRONAME:something3")
        ns.register("test.other.a","PYRONAME:somethingA")
        ns.register("test.other.b","PYRONAME:somethingB")
        ns.register("test.other.c","PYRONAME:somethingC")
        ns.register("entirely.else","PYRONAME:meh")
        objects=ns.list()
        self.assertEqual(7,len(objects))
        objects=ns.list(prefix="nothing")
        self.assertEqual(0,len(objects))
        objects=ns.list(prefix="test.")
        self.assertEqual(6,len(objects))
        objects=ns.list(regex=r".+other..")
        self.assertEqual(3,len(objects))
        self.assertTrue("test.other.a" in objects)
        self.assertEqual("PYRONAME:somethingA", objects["test.other.a"])
        objects=ns.list(regex=r"\d\d\d\d\d\d\d\d\d\d")
        self.assertEqual(0,len(objects))

    def testNameserverWithStmt(self):
        ns=Pyro.naming.NameServerDaemon(port=0)
        self.assertFalse(ns.nameserver is None)
        ns.close()
        self.assertTrue(ns.nameserver is None)
        with Pyro.naming.NameServerDaemon(port=0) as ns:
            self.assertFalse(ns.nameserver is None)
            pass
        self.assertTrue(ns.nameserver is None)
        try:
            with Pyro.naming.NameServerDaemon(port=0) as ns:
                self.assertFalse(ns.nameserver is None)
                print 1/0 # cause an error
            self.fail("expected error")
        except ZeroDivisionError: 
            pass
        self.assertTrue(ns.nameserver is None)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
