import unittest
import Pyro.core
import Pyro.constants
import Pyro.config
from Pyro.errors import *

class DaemonTests(unittest.TestCase):
    # We create a daemon, but notice that we are not actually running the requestloop
    # 'on-line' tests are all taking place in the NamingTests
    
    def testDaemon(self):
        try:
            Pyro.config.PORT+=1   # avoid double binding
            d=Pyro.core.Daemon()
            defaultLocation="%s:%d" %(Pyro.config.HOST, Pyro.config.PORT)
            self.assertEqual( defaultLocation, d.locationStr)
            self.assertTrue(Pyro.constants.INTERNAL_DAEMON_GUID in d.objectsById)
            self.assertTrue(Pyro.constants.DAEMON_LOCALNAME in d.objectsByName)
            self.assertEqual(d.resolve(Pyro.constants.DAEMON_LOCALNAME).object, Pyro.constants.INTERNAL_DAEMON_GUID)
            self.assertEqual("PYRO:"+Pyro.constants.INTERNAL_DAEMON_GUID+"@"+defaultLocation, str(d.uriFor(name=Pyro.constants.INTERNAL_DAEMON_GUID)))
        finally:
            d.shutdown()
        
    def testRegisterEtc(self):
        class MyObj(object):
            def __init__(self, arg):
                self.arg=arg
            def __eq__(self,other):
                return self.arg==other.arg
        try:
            Pyro.config.PORT+=1  # avoid double binding
            d=Pyro.core.Daemon()
            defaultLocation="%s:%d" %(Pyro.config.HOST, Pyro.config.PORT)
            self.assertEquals(1, len(d.objectsById))
            self.assertEquals(1, len(d.registeredObjects()))
           
            o1=MyObj("object1")
            o2=MyObj("object2")
            d.register(o1, None)
            self.assertRaises(DaemonError, d.register, o1, None)
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
            self.assertRaises(DaemonError, d.uriFor, o1, pyroloc=True)  #can't get a pyroloc for an object without name
            u2=d.uriFor(name=o2._pyroObjectId)
            u3=d.uriFor(name="unexisting_thingie",pyroloc=True)
            u4=d.uriFor(o2,pyroloc=True)
            self.assertEquals(Pyro.core.PyroURI, type(u1))
            self.assertEquals("PYRO",u1.protocol)
            self.assertEquals("PYROLOC",u3.protocol)
            self.assertEquals("PYROLOC",u4.protocol)
            self.assertEquals("obj2a",u4.object)
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
        finally:
            d.shutdown()


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()