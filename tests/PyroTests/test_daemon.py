"""
Tests for the daemon.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import os, time, socket
import unittest
import Pyro4.core
import Pyro4.constants
import Pyro4.socketutil
from Pyro4.errors import DaemonError,PyroError
from testsupport import *

Pyro4.config.reset(useenvironment=False)


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
        Pyro4.config.POLLTIMEOUT=0.1
        Pyro4.config.HMAC_KEY=tobytes("testsuite")
    def tearDown(self):
        Pyro4.config.HMAC_KEY=None
        
    def testDaemon(self):
        freeport=Pyro4.socketutil.findProbablyUnusedPort()
        with Pyro4.core.Daemon(port=freeport) as d:
            locationstr="%s:%d" %(Pyro4.config.HOST, freeport)
            self.assertEqual( locationstr, d.locationStr)
            self.assertTrue(Pyro4.constants.DAEMON_NAME in d.objectsById)
            self.assertEqual("PYRO:"+Pyro4.constants.DAEMON_NAME+"@"+locationstr, str(d.uriFor(Pyro4.constants.DAEMON_NAME)))
            # check the string representations
            expected=("<Pyro4.core.Daemon at 0x%x, %s, 1 objects>") % (id(d), locationstr)
            self.assertEqual(expected,str(d))
            self.assertEqual(expected,unicode(d))
            self.assertEqual(expected,repr(d))
            sockname=d.sock.getsockname()
            self.assertEqual(freeport, sockname[1])
            daemonobj=d.objectsById[Pyro4.constants.DAEMON_NAME]
            daemonobj.ping()
            daemonobj.registered()
            try:
                daemonobj.shutdown()
                self.fail("should not succeed to call unexposed method")
            except AttributeError:
                pass

    def testDaemonUnixSocket(self):
        if hasattr(socket,"AF_UNIX"):
            SOCKNAME="test_unixsocket"
            with Pyro4.core.Daemon(unixsocket=SOCKNAME) as d:
                locationstr="./u:"+SOCKNAME
                self.assertEqual(locationstr, d.locationStr)
                self.assertEqual("PYRO:"+Pyro4.constants.DAEMON_NAME+"@"+locationstr, str(d.uriFor(Pyro4.constants.DAEMON_NAME)))
                # check the string representations
                expected=("<Pyro4.core.Daemon at 0x%x, %s, 1 objects>") % (id(d), locationstr)
                self.assertEqual(expected,str(d))
                self.assertEqual(SOCKNAME,d.sock.getsockname())
                self.assertEqual(socket.AF_UNIX,d.sock.family)

    def testServertypeThread(self):
        old_servertype=Pyro4.config.SERVERTYPE
        Pyro4.config.SERVERTYPE="thread"
        with Pyro4.core.Daemon(port=0) as d:
            sock=d.sock
            self.assertTrue(sock in d.sockets, "daemon's socketlist should contain the server socket")
            self.assertTrue(len(d.sockets)==1, "daemon without connections should have just 1 socket")
        Pyro4.config.SERVERTYPE=old_servertype

    def testServertypeMultiplex(self):
        old_servertype=Pyro4.config.SERVERTYPE
        Pyro4.config.SERVERTYPE="multiplex"
        # this type is not supported in Jython
        if os.name=="java":
            self.assertRaises(NotImplementedError, Pyro4.core.Daemon, port=0)
        else:
            with Pyro4.core.Daemon(port=0) as d:
                sock=d.sock
                self.assertTrue(sock in d.sockets, "daemon's socketlist should contain the server socket")
                self.assertTrue(len(d.sockets)==1, "daemon without connections should have just 1 socket")
        Pyro4.config.SERVERTYPE=old_servertype
                
    def testServertypeFoobar(self):
        old_servertype=Pyro4.config.SERVERTYPE
        Pyro4.config.SERVERTYPE="foobar"
        self.assertRaises(PyroError, Pyro4.core.Daemon)
        Pyro4.config.SERVERTYPE=old_servertype

    def testRegisterEtc(self):
        freeport=Pyro4.socketutil.findProbablyUnusedPort()
        d=Pyro4.core.Daemon(port=freeport)
        try:
            self.assertEqual(1, len(d.objectsById))
            o1=MyObj("object1")
            o2=MyObj("object2")
            d.register(o1)
            self.assertRaises(DaemonError, d.register, o2, Pyro4.constants.DAEMON_NAME)  # cannot use daemon name
            self.assertRaises(DaemonError, d.register, o1, None)  # cannot register twice
            self.assertRaises(DaemonError, d.register, o1, "obj1a")
            d.register(o2, "obj2a")
            self.assertRaises(DaemonError, d.register, o2, "obj2b")
            
            self.assertEqual(3, len(d.objectsById))
            self.assertEqual(o1, d.objectsById[o1._pyroId])
            self.assertEqual(o2, d.objectsById["obj2a"])
            self.assertEqual("obj2a", o2._pyroId)
            self.assertEqual(d, o2._pyroDaemon)
    
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
            # no more _pyro attributs must remain after unregistering
            for attr in vars(o2):
                self.assertFalse(attr.startswith("_pyro"))
            self.assertEqual(1, len(d.objectsById))
            self.assertFalse(objectid in d.objectsById)
            self.assertRaises(DaemonError, d.unregister, [1,2,3])
            
            # test unregister daemon name
            d.unregister(Pyro4.constants.DAEMON_NAME)
            self.assertTrue(Pyro4.constants.DAEMON_NAME in d.objectsById)
            
            # weird args
            w=MyObj("weird")
            self.assertRaises(AttributeError, d.register, None)
            self.assertRaises(AttributeError, d.register, 4444)
            self.assertRaises(TypeError, d.register, w, 666)
            
            # uri return value from register
            uri=d.register(MyObj("xyz"))
            self.assertTrue(isinstance(uri, Pyro4.core.URI))
            uri=d.register(MyObj("xyz"), "test.register")
            self.assertTrue("test.register", uri.object)

        finally:
            d.close()

    def testRegisterUnicode(self):
        with Pyro4.core.Daemon(port=0) as d:
            myobj1=MyObj("hello1")
            myobj2=MyObj("hello2")
            myobj3=MyObj("hello3")
            uri1=d.register(myobj1, "str_name")
            uri2=d.register(myobj2, unicode("unicode_name"))
            uri3=d.register(myobj3, "unicode_"+unichr(0x20ac))
            self.assertEqual(4, len(d.objectsById))
            uri=d.uriFor(myobj1)
            self.assertEqual(uri1,uri)
            _=Pyro4.core.Proxy(uri)
            uri=d.uriFor(myobj2)
            self.assertEqual(uri2,uri)
            _=Pyro4.core.Proxy(uri)
            uri=d.uriFor(myobj3)
            self.assertEqual(uri3,uri)
            _=Pyro4.core.Proxy(uri)
            uri=d.uriFor("str_name")
            self.assertEqual(uri1,uri)
            _=Pyro4.core.Proxy(uri)
            uri=d.uriFor(unicode("unicode_name"))
            self.assertEqual(uri2,uri)
            _=Pyro4.core.Proxy(uri)
            uri=d.uriFor("unicode_"+unichr(0x20ac))
            self.assertEqual(uri3,uri)
            _=Pyro4.core.Proxy(uri)

    def testDaemonObject(self):
        with Pyro4.core.Daemon(port=0) as d:
            daemon=Pyro4.core.DaemonObject(d)
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
        freeport=Pyro4.socketutil.findProbablyUnusedPort()
        d=Pyro4.core.Daemon(port=freeport)
        try:
            locationstr="%s:%d" %(Pyro4.config.HOST, freeport)
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
            self.assertEqual(Pyro4.core.URI, type(u1))
            self.assertEqual("PYRO",u1.protocol)
            self.assertEqual("PYRO",u2.protocol)
            self.assertEqual("PYRO",u3.protocol)
            self.assertEqual("PYRO",u4.protocol)
            self.assertEqual("object_two",u4.object)
            self.assertEqual(Pyro4.core.URI("PYRO:unexisting_thingie@"+locationstr), u3)
        finally:
            d.close()
    
    def testDaemonWithStmt(self):
        d=Pyro4.core.Daemon()
        self.assertTrue(d.transportServer is not None)
        d.close()   # closes the transportserver and sets it to None
        self.assertTrue(d.transportServer is None)
        with Pyro4.core.Daemon() as d:
            self.assertTrue(d.transportServer is not None)
            pass
        self.assertTrue(d.transportServer is None)
        try:
            with Pyro4.core.Daemon() as d:
                print(1//0) # cause an error
            self.fail("expected error")
        except ZeroDivisionError: 
            pass
        self.assertTrue(d.transportServer is None)
        d=Pyro4.core.Daemon()
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
        with Pyro4.core.Daemon(port=0) as d:
            condition=lambda:False
            start=time.time()
            d.requestLoop(loopCondition=condition)   #this should return almost immediately
            duration=time.time()-start
            self.assertAlmostEqual(0.0, duration, places=1)

    def testNAT(self):
        with Pyro4.core.Daemon() as d:
            self.assertTrue(d.natLocationStr is None)
        with Pyro4.core.Daemon(nathost="nathosttest", natport=12345) as d:
            self.assertEqual("nathosttest:12345", d.natLocationStr)
            self.assertNotEqual(d.locationStr, d.natLocationStr)
            uri=d.register(MyObj(1))
            self.assertEqual("nathosttest:12345", uri.location)
            uri=d.uriFor("object")
            self.assertEqual("nathosttest:12345", uri.location)
            uri=d.uriFor("object", nat=False)
            self.assertNotEqual("nathosttest:12345", uri.location)
        try:
            d=Pyro4.core.Daemon(nathost="bla")
            self.fail("expected error")
        except ValueError:
            pass
        try:
            d=Pyro4.core.Daemon(natport=5555)
            self.fail("expected error")
        except ValueError:
            pass
        try:
            d=Pyro4.core.Daemon(nathost="bla", natport=5555, unixsocket="testsock")
            self.fail("expected error")
        except ValueError:
            pass

    def testNATconfig(self):
        try:
            Pyro4.config.NATHOST=None
            Pyro4.config.NATPORT=0
            with Pyro4.core.Daemon() as d:
                self.assertTrue(d.natLocationStr is None)
            Pyro4.config.NATHOST="nathosttest"
            Pyro4.config.NATPORT=12345
            with Pyro4.core.Daemon() as d:
                self.assertEqual("nathosttest:12345", d.natLocationStr)
        finally:
            Pyro4.config.NATHOST=None
            Pyro4.config.NATPORT=0

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
