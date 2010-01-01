import unittest
import Pyro.naming
from Pyro.errors import NamingError

# offline name-server tests

class OfflineTests(unittest.TestCase):
    def testRegister(self):
        ns=Pyro.naming.NameServer()
        ns.ping()
        ns.register("test.object1","PYRO:111111@host.com")  # can register string or PyroURI
        ns.register("test.object2","PYRO:222222@host.com")
        ns.register("test.object3","PYRO:333333@host.com")
        ns.register("test.sub.objectA",Pyro.core.PyroURI("PYRO:AAAAAA@host.com"))
        ns.register("test.sub.objectB",Pyro.core.PyroURI("PYRO:BBBBBB@host.com"))
        
        self.assertRaises(NamingError, ns.lookup, "unknown_object")
        
        uri=ns.lookup("test.object3")
        self.assertEqual(Pyro.core.PyroURI("PYRO:333333@host.com"), uri)   # lookup always returns PyroURI
        ns.remove("unknown_object")
        ns.remove("test.object1")
        ns.remove("test.object2")
        ns.remove("test.object3")
        all=ns.list()
        self.assertEqual(2, len(all))  # 2 leftover objects
    def testList(self):
        ns=Pyro.naming.NameServer()
        ns.register("test.objects.1","SOMETHING1")
        ns.register("test.objects.2","SOMETHING2")
        ns.register("test.objects.3","SOMETHING3")
        ns.register("test.other.a","SOMETHINGA")
        ns.register("test.other.b","SOMETHINGB")
        ns.register("test.other.c","SOMETHINGC")
        ns.register("entirely.else","MEH")
        objects=ns.list()
        self.assertEqual(7,len(objects))
        objects=ns.list(prefix="nothing")
        self.assertEqual(0,len(objects))
        objects=ns.list(prefix="test.")
        self.assertEqual(6,len(objects))
        objects=ns.list(regex=r".+other..")
        self.assertEqual(3,len(objects))
        self.assertTrue("test.other.a" in objects)
        self.assertEqual("SOMETHINGA", objects["test.other.a"])
        objects=ns.list(regex=r"\d\d\d\d\d\d\d\d\d\d")
        self.assertEqual(0,len(objects))
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
