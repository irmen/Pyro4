import unittest
import Pyro.core
import Pyro.constants
import Pyro.config
from Pyro.errors import *

class DaemonTests(unittest.TestCase):

    def setUp(self):
        self.daemon=Pyro.core.Daemon()
    def tearDown(self):
        self.daemon.close()
        
    def testDaemon(self):
        d=self.daemon
        defaultLocation="%s:%d" %(Pyro.config.DEFAULT_SERVERHOST, Pyro.config.DEFAULT_PORT)
        self.assertEqual( defaultLocation, d.locationStr)
        self.assertTrue(d._pyroUri is None)
        self.assertTrue(d._pyroObjectId, Pyro.constants.INTERNAL_DAEMON_GUID)
        self.assertTrue(Pyro.constants.INTERNAL_DAEMON_GUID in d.objectsById)
        self.assertTrue(Pyro.constants.DAEMON_LOCALNAME in d.objectsByName)
        self.assertEqual(d.resolve(Pyro.constants.DAEMON_LOCALNAME).object, Pyro.constants.INTERNAL_DAEMON_GUID)
        self.assertEqual("PYRO:"+Pyro.constants.INTERNAL_DAEMON_GUID+"@"+defaultLocation, str(d.uriFor(d)))
        
    def testRegisterEtc(self):
        d=self.daemon
        defaultLocation="%s:%d" %(Pyro.config.DEFAULT_SERVERHOST, Pyro.config.DEFAULT_PORT)
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

        # test uriFor
        u1=d.uriFor(o1)
        u2=d.uriFor(o2._pyroObjectId)
        u3=d.uriFor("unexisting_thingie",True)
        self.assertEquals(Pyro.core.PyroURI, type(u1))
        self.assertEquals("PYRO",u1.protocol)
        self.assertEquals("PYROLOC",u3.protocol)
        self.assertEquals(Pyro.core.PyroURI("PYROLOC:unexisting_thingie@"+defaultLocation), u3)

        # test unregister
        d.unregister("unexisting_thingie")
        d.unregister(None)
        d.unregister("obj2a")
        d.unregister(o1._pyroObjectId)
        self.assertEqual(1, len(d.objectsById))
        self.assertEqual(1, len(d.registeredObjects()))
        self.assertTrue(o1._pyroObjectId not in d.objectsById)
        self.assertTrue(o2._pyroObjectId not in d.objectsById)
        

        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()