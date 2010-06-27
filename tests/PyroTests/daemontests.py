"""
Tests for the daemon.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong.
irmen@razorvine.net - http://www.razorvine.net/python/Pyro
"""

from __future__ import with_statement
import os, time, sys
import unittest
import Pyro.core
import Pyro.constants
import Pyro.config
import Pyro.socketutil
from Pyro.errors import DaemonError,PyroError

if sys.version_info>=(3,0):
    unicode=str
    unichr=chr


class MyObj(object):
    def __init__(self, arg):
        self.arg=arg
    def __eq__(self,other):
        return self.arg==other.arg
    __hash__=object.__hash__

class DaemonTests(unittest.TestCase):
    # We create a daemon, but notice that we are not actually running the requestloop.
    # 'on-line' tests are all taking place in another test, to keep this one simple.

    def setUp(self):
        Pyro.config.POLLTIMEOUT=0.1

    def testDaemon(self):
        freeport=Pyro.socketutil.findUnusedPort()
        with Pyro.core.Daemon(port=freeport) as d:
            locationstr="%s:%d" %(Pyro.config.HOST, freeport)
            self.assertEqual( locationstr, d.locationStr)
            self.assertTrue(Pyro.constants.DAEMON_NAME in d.objectsById)
            self.assertEqual("PYRO:"+Pyro.constants.DAEMON_NAME+"@"+locationstr, str(d.uriFor(Pyro.constants.DAEMON_NAME)))
            # check the string representations
            self.assertEqual("<Pyro Daemon on "+locationstr+">",str(d))
            self.assertEqual("<Pyro Daemon on "+locationstr+">",unicode(d))
            self.assertTrue("Daemon object at" in repr(d))
            sockname=d.sock.getsockname()
            self.assertEqual(freeport, sockname[1])
            daemonobj=d.objectsById[Pyro.constants.DAEMON_NAME]
            daemonobj.ping()
            daemonobj.registered()
            try:
                daemonobj.shutdown()
                self.fail("should not succeed to call unexposed method")
            except AttributeError:
                pass

    def testServertypeThread(self):
        old_servertype=Pyro.config.SERVERTYPE
        Pyro.config.SERVERTYPE="thread"
        with Pyro.core.Daemon(port=0) as d:
            sock=d.sock
            sockets=d.sockets()
            self.assertTrue(sock in sockets, "daemon's socketlist should contain the server socket")
            self.assertTrue(len(sockets)==1, "daemon without connections should have just 1 socket")
        Pyro.config.SERVERTYPE=old_servertype

    def testServertypeSelect(self):
        old_servertype=Pyro.config.SERVERTYPE
        Pyro.config.SERVERTYPE="select"
        # this type is not supported in Jython
        if os.name=="java":
            self.assertRaises(NotImplementedError, Pyro.core.Daemon, port=0)
        else:
            with Pyro.core.Daemon(port=0) as d:
                sock=d.sock
                sockets=d.sockets()
                self.assertTrue(sock in sockets, "daemon's socketlist should contain the server socket")
                self.assertTrue(len(sockets)==1, "daemon without connections should have just 1 socket")
        Pyro.config.SERVERTYPE=old_servertype
                
    def testServertypeFoobar(self):
        old_servertype=Pyro.config.SERVERTYPE
        Pyro.config.SERVERTYPE="foobar"
        self.assertRaises(PyroError, Pyro.core.Daemon)
        Pyro.config.SERVERTYPE=old_servertype

    def testRegisterEtc(self):
        try:
            freeport=Pyro.socketutil.findUnusedPort()
            d=Pyro.core.Daemon(port=freeport)
            self.assertEquals(1, len(d.objectsById))
            o1=MyObj("object1")
            o2=MyObj("object2")
            d.register(o1)
            self.assertRaises(DaemonError, d.register, o2, Pyro.constants.DAEMON_NAME)  # cannot use daemon name
            self.assertRaises(DaemonError, d.register, o1, None)  # cannot register twice
            self.assertRaises(DaemonError, d.register, o1, "obj1a")
            d.register(o2, "obj2a")
            self.assertRaises(DaemonError, d.register, o2, "obj2b")
            
            self.assertEqual(3, len(d.objectsById))
            self.assertEquals(o1, d.objectsById[o1._pyroId])
            self.assertEquals(o2, d.objectsById["obj2a"])
            self.assertEquals("obj2a", o2._pyroId)
            self.assertEquals(d, o2._pyroDaemon)
    
            # test unregister
            d.unregister("unexisting_thingie")
            self.assertRaises(ValueError, d.unregister, None)
            d.unregister("obj2a")
            d.unregister(o1._pyroId)
            self.assertEqual(1, len(d.objectsById))
            self.assertTrue(o1._pyroId not in d.objectsById)
            self.assertTrue(o2._pyroId not in d.objectsById)
            
            # test unregister objects
            del o2._pyroId
            d.register(o2)
            objectid = o2._pyroId
            self.assertTrue(objectid in d.objectsById)
            self.assertEqual(2, len(d.objectsById))
            d.unregister(o2)
            self.assertFalse(hasattr(o2, "_pyroId"))
            self.assertFalse(hasattr(o2, "_pyroDaemon"))
            self.assertEqual(1, len(d.objectsById))
            self.assertFalse(objectid in d.objectsById)
            self.assertRaises(DaemonError, d.unregister, [1,2,3])
            
            # test unregister daemon name
            d.unregister(Pyro.constants.DAEMON_NAME)
            self.assertTrue(Pyro.constants.DAEMON_NAME in d.objectsById)
            
            # weird args
            w=MyObj("weird")
            self.assertRaises(AttributeError, d.register, None)
            self.assertRaises(AttributeError, d.register, 4444)
            self.assertRaises(TypeError, d.register, w, 666)
            
            # uri return value from register
            uri=d.register(MyObj("xyz"))
            self.assertTrue(isinstance(uri, Pyro.core.URI))
            uri=d.register(MyObj("xyz"), "test.register")
            self.assertTrue("test.register", uri.object)

        finally:
            d.close()

    def testRegisterUnicode(self):
        with Pyro.core.Daemon(port=0) as d:
            myobj1=MyObj("hello1")
            myobj2=MyObj("hello2")
            myobj3=MyObj("hello3")
            uri1=d.register(myobj1, "str_name")
            uri2=d.register(myobj2, unicode("unicode_name"))
            uri3=d.register(myobj3, "unicode_"+unichr(0x20ac))
            self.assertEqual(4, len(d.objectsById))
            uri=d.uriFor(myobj1)
            self.assertEqual(uri1,uri)
            p=Pyro.core.Proxy(uri)
            uri=d.uriFor(myobj2)
            self.assertEqual(uri2,uri)
            p=Pyro.core.Proxy(uri)
            uri=d.uriFor(myobj3)
            self.assertEqual(uri3,uri)
            p=Pyro.core.Proxy(uri)
            uri=d.uriFor("str_name")
            self.assertEqual(uri1,uri)
            p=Pyro.core.Proxy(uri)
            uri=d.uriFor(unicode("unicode_name"))
            self.assertEqual(uri2,uri)
            p=Pyro.core.Proxy(uri)
            uri=d.uriFor("unicode_"+unichr(0x20ac))
            self.assertEqual(uri3,uri)
            p=Pyro.core.Proxy(uri)

    def testDaemonObject(self):
        with Pyro.core.Daemon(port=0) as d:
            daemon=Pyro.core.DaemonObject(d)
            obj1=MyObj("object1")
            obj2=MyObj("object2")
            obj3=MyObj("object2")
            d.register(obj1,"obj1")
            d.register(obj2,"obj2")
            d.register(obj3)
            daemon.ping()
            registered=daemon.registered()
            self.assertTrue(type(registered) is list)
            self.assertEqual(4, len(registered))
            self.assertTrue("obj1" in registered)
            self.assertTrue("obj2" in registered)
            self.assertTrue(obj3._pyroId in registered)
            try:
                daemon.shutdown()
                self.fail("should not succeed to call unexposed method")
            except AttributeError:
                pass
        
    def testUriFor(self):
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
            o3=MyObj("object3")
            self.assertRaises(DaemonError, d.uriFor, o3)  #can't get an uri for an unregistered object (note: unregistered name is allright)
            u1=d.uriFor(o1)
            u2=d.uriFor(o2._pyroId)
            u3=d.uriFor("unexisting_thingie")  # unregistered name is no problem, it's just an uri we're requesting
            u4=d.uriFor(o2)
            self.assertEquals(Pyro.core.URI, type(u1))
            self.assertEquals("PYRO",u1.protocol)
            self.assertEquals("PYRO",u2.protocol)
            self.assertEquals("PYRO",u3.protocol)
            self.assertEquals("PYRO",u4.protocol)
            self.assertEquals("object_two",u4.object)
            self.assertEquals(Pyro.core.URI("PYRO:unexisting_thingie@"+locationstr), u3)
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
                print(1//0) # cause an error
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
        
    def testRequestloopCondition(self):
        with Pyro.core.Daemon(port=0) as d:
            condition=lambda:False
            start=time.time()
            d.requestLoop(loopCondition=condition)   #this should return almost immediately
            duration=time.time()-start
            self.assertAlmostEqual(0.0, duration, places=1)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
