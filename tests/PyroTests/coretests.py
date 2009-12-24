import unittest

import Pyro.core

class CoreTests(unittest.TestCase):

    def testUriStr(self):
        p=Pyro.core.PyroURI("PYRONAME:some_obj_name")
        self.assertEqual("PYRONAME:some_obj_name",str(p))
        p=Pyro.core.PyroURI("PYRO:12345@host.com:9999")
        self.assertEqual("PYRO:12345@host.com:9999",str(p))
        p=Pyro.core.PyroURI("PYRO:12345@./p:pipename")
        self.assertEqual("PYRO:12345@./p:pipename",str(p))
        p=Pyro.core.PyroURI("PYRO:12345@./u:sockname")
        self.assertEqual("PYRO:12345@./u:sockname",str(p))
    def testUriParsing(self):
        p=Pyro.core.PyroURI("PYRONAME:some_obj_name")
        self.assertEqual("PYRONAME",p.protocol)
        self.assertEqual("some_obj_name",p.object)
        self.assertEqual(None,p.host)
        self.assertEqual(None,p.pipename)
        self.assertEqual(None,p.sockname)
        self.assertEqual(None,p.port)

        p=Pyro.core.PyroURI("PYRO:12345@host.com")
        self.assertEqual("PYRO",p.protocol)
        self.assertEqual("12345",p.object)
        self.assertEqual("host.com",p.host)
        self.assertEqual(None,p.pipename)
        self.assertEqual(None,p.sockname)
        self.assertEqual(Pyro.core.DEFAULT_PORT,p.port)
        p=Pyro.core.PyroURI("PYRO:12345@host.com:9999")
        self.assertEqual("host.com",p.host)
        self.assertEqual(9999,p.port)

        p=Pyro.core.PyroURI("PYRO:12345@./p:pipename")
        self.assertEqual("12345",p.object)
        self.assertEqual("pipename",p.pipename)
        p=Pyro.core.PyroURI("PYRO:12345@./u:sockname")
        self.assertEqual("12345",p.object)
        self.assertEqual("sockname",p.sockname)
    def testUriEqual(self):
        p1=Pyro.core.PyroURI("PYRO:12345@host.com:9999")
        p2=Pyro.core.PyroURI("PYRO:12345@host.com:9999")
        p3=Pyro.core.PyroURI("PYRO:99999@host.com:4444")
        self.assertEqual(p1,p2)
        self.assertNotEqual(p1,p3)
        self.assertNotEqual(p2,p3)
        p2.port=4444
        p2.object="99999"
        self.assertNotEqual(p1,p2)
        self.assertEqual(p2,p3)
    def testUriPickle(self):
        import pickle
        p=Pyro.core.PyroURI("PYRO:12345@host.com:9999")
        q=pickle.dumps(p, pickle.HIGHEST_PROTOCOL)
        p2=pickle.loads(q)
        self.assertEqual(p2,p)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()