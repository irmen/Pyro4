import unittest
import Pyro.core
import Pyro.constants
import Pyro.config
from Pyro.errors import *

class DaemonTests(unittest.TestCase):

    def testDaemon(self):
        d=Pyro.core.Daemon()
        self.assertEqual( ("127.0.0.1",Pyro.config.DEFAULT_PORT), d.location)
        self.assertTrue(d._pyroUri is None)
        self.assertTrue(d._pyroObjectId, Pyro.constants.INTERNAL_DAEMON_GUID)
        self.assertTrue(Pyro.constants.INTERNAL_DAEMON_GUID in d.objectsById)
        self.assertTrue(Pyro.constants.DAEMON_NAME in d.objectsByName)
        self.assertEqual(d.resolve(Pyro.constants.DAEMON_NAME).object, Pyro.constants.INTERNAL_DAEMON_GUID)
        self.assertEqual("PYRO:"+Pyro.constants.INTERNAL_DAEMON_GUID+"@127.0.0.1:7766", str(d.uriFor(d)))
        d.close()
        
    def testRegister(self):
        d=Pyro.core.Daemon()
        self.assertEquals(1, len(d.objectsById))
        self.assertEquals(1, len(d.registeredObjects()))
        
        class MyObj(Pyro.core.ObjBase):
            def __eq__(self,other):
                return self._pyroObjectId==other._pyroObjectId
        
        o1=MyObj()
        o2=MyObj()
        d.register(o1, None)
        self.assertRaises(DaemonError, d.register, o1, "obj1a")
        d.register(o2, "obj2a")
        self.assertRaises(DaemonError, d.register, o2, "obj2b")
        
        self.assertEqual(3, len(d.objectsById))
        self.assertEqual(2, len(d.registeredObjects()))
        self.assertEqual(o2._pyroObjectId, d.resolve("obj2a").object)
        self.assertEqual((None,o1), d.objectsById[o1._pyroObjectId])
        self.assertEqual(("obj2a",o2), d.objectsById[o2._pyroObjectId])
        
        d.unregister("unexisting_thingie")
        d.unregister(None)
        d.unregister("obj2a")
        d.unregister(o1._pyroObjectId)
        self.assertEqual(1, len(d.objectsById))
        self.assertEqual(1, len(d.registeredObjects()))
        self.assertTrue(o1._pyroObjectId not in d.objectsById)
        self.assertTrue(o2._pyroObjectId not in d.objectsById)
        
        d.close()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()