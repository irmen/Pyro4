import unittest
import Pyro.core
import Pyro.constants
import Pyro.config
import Pyro.socketutil
from Pyro.errors import DaemonError,PyroError

class DaemonTests(unittest.TestCase):
    # We create a daemon, but notice that we are not actually running the requestloop.
    # 'on-line' tests are all taking place in another test, to keep this one simple.
    
    def testDaemon(self):
        try:
            freeport=Pyro.socketutil.findUnusedPort()
            d=Pyro.core.Daemon(port=freeport)
            locationstr="%s:%d" %(Pyro.config.HOST, freeport)
            self.assertEqual( locationstr, d.locationStr)
            self.assertTrue(Pyro.constants.INTERNAL_DAEMON_GUID in d.objectsById)
            self.assertTrue(Pyro.constants.DAEMON_LOCALNAME in d.objectsByName)
            self.assertEqual(d.resolve(Pyro.constants.DAEMON_LOCALNAME).object, Pyro.constants.INTERNAL_DAEMON_GUID)
            self.assertEqual("PYRO:"+Pyro.constants.INTERNAL_DAEMON_GUID+"@"+locationstr, str(d.uriFor(Pyro.constants.INTERNAL_DAEMON_GUID)))
        finally:
            d.close()
        
    def testRegisterEtc(self):
        class MyObj(object):
            def __init__(self, arg):
                self.arg=arg
            def __eq__(self,other):
                return self.arg==other.arg
            __hash__=object.__hash__
        try:
            freeport=Pyro.socketutil.findUnusedPort()
            d=Pyro.core.Daemon(port=freeport)
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
            d.close()

    def testUriFor(self):
        class MyObj(object):
            def __init__(self, arg):
                self.arg=arg
            def __eq__(self,other):
                return self.arg==other.arg
            __hash__=object.__hash__
        try:
            freeport=Pyro.socketutil.findUnusedPort()
            d=Pyro.core.Daemon(port=freeport)
            locationstr="%s:%d" %(Pyro.config.HOST, freeport)
            o1=MyObj("object1")
            o2=MyObj("object2")
            self.assertRaises(DaemonError, d.uriFor, o1)
            self.assertRaises(DaemonError, d.uriFor, o2)
            d.register(o1,None)
            d.register(o2,"object_two")
            self.assertRaises(DaemonError, d.uriFor, o1, pyroloc=True)  #can't get a pyroloc for an object without name
            u1=d.uriFor(o1)
            u2=d.uriFor(o2._pyroObjectId)
            u3=d.uriFor("unexisting_thingie",pyroloc=True)
            u4=d.uriFor(o2,pyroloc=True)
            self.assertEquals(Pyro.core.PyroURI, type(u1))
            self.assertEquals("PYRO",u1.protocol)
            self.assertEquals("PYROLOC",u3.protocol)
            self.assertEquals("PYROLOC",u4.protocol)
            self.assertEquals("object_two",u4.object)
            self.assertEquals(Pyro.core.PyroURI("PYROLOC:unexisting_thingie@"+locationstr), u3)
        finally:
            d.close()
    
    def testDaemonWithStmt(self):
        d=Pyro.core.Daemon()
        self.assertTrue(d.transportServer is not None)
        d.close()   # closes the transportserver and sets it to None
        self.assertTrue(d.transportServer is None)
        with Pyro.core.Daemon() as d:
            self.assertTrue(d.transportServer is not None)
            pass
        self.assertTrue(d.transportServer is None)
        try:
            with Pyro.core.Daemon() as d:
                print 1//0 # cause an error
            self.fail("expected error")
        except ZeroDivisionError: 
            pass
        self.assertTrue(d.transportServer is None)
        d=Pyro.core.Daemon()
        with d:
            pass
        try:
            with d:
                pass
            self.fail("expected error")
        except PyroError:
            # you cannot re-use a daemon object in multiple with statements
            pass
        d.close()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()