"""
Tests for the name server (offline/basic logic).

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import unittest
import sys, select, os
import Pyro4.core
import Pyro4.naming
import Pyro4.nsc
import Pyro4.constants
import Pyro4.socketutil
from Pyro4.errors import NamingError,PyroError
from testsupport import *


class OfflineNameServerTests(unittest.TestCase):
    def setUp(self):
        Pyro4.config.HMAC_KEY=tobytes("testsuite")
    def tearDown(self):
        Pyro4.config.HMAC_KEY=None
    def testRegister(self):
        ns=Pyro4.naming.NameServer()
        ns.ping()
        ns.register("test.object1","PYRO:000000@host.com:4444")
        ns.register("test.object2","PYRO:222222@host.com:4444")
        ns.register("test.object3","PYRO:333333@host.com:4444")
        self.assertEqual("PYRO:000000@host.com:4444",str(ns.lookup("test.object1")))
        ns.register("test.object1","PYRO:111111@host.com:4444")  # registering again should be ok by default
        self.assertEqual("PYRO:111111@host.com:4444",str(ns.lookup("test.object1")), "should be new uri")
        ns.register("test.sub.objectA",Pyro4.core.URI("PYRO:AAAAAA@host.com:4444"))
        ns.register("test.sub.objectB",Pyro4.core.URI("PYRO:BBBBBB@host.com:4444"))

        # if safe=True, a registration of an existing name shoould give a NamingError
        self.assertRaises(NamingError, ns.register, "test.object1", "PYRO:X@Y:5555", safe=True)

        self.assertRaises(TypeError, ns.register, None, None)
        self.assertRaises(TypeError, ns.register, 4444, 4444)
        self.assertRaises(TypeError, ns.register, "test.wrongtype", 4444)
        self.assertRaises(TypeError, ns.register, 4444, "PYRO:X@Y:5555")

        self.assertRaises(NamingError, ns.lookup, "unknown_object")
        
        uri=ns.lookup("test.object3")
        self.assertEqual(Pyro4.core.URI("PYRO:333333@host.com:4444"), uri)   # lookup always returns URI
        ns.remove("unknown_object")
        ns.remove("test.object1")
        ns.remove("test.object2")
        ns.remove("test.object3")
        all=ns.list()
        self.assertEqual(2, len(all))  # 2 leftover objects

        self.assertRaises(PyroError, ns.register, "test.nonurivalue", "THISVALUEISNOTANURI")

    def testRemove(self):
        ns=Pyro4.naming.NameServer()
        ns.register(Pyro4.constants.NAMESERVER_NAME, "PYRO:nameserver@host:555")
        for i in range(20):
            ns.register("test.%d" % i, "PYRO:obj@host:555")
        self.assertEqual(21, len(ns.list()))
        self.assertEqual(0, ns.remove("wrong"))
        self.assertEqual(0, ns.remove(prefix="wrong"))
        self.assertEqual(0, ns.remove(regex="wrong.*"))
        self.assertEqual(1, ns.remove("test.0"))
        self.assertEqual(20, len(ns.list()))
        self.assertEqual(11, ns.remove(prefix="test.1"))  # 1, 10-19
        self.assertEqual(8, ns.remove(regex=r"test\.."))  # 2-9
        self.assertEqual(1, len(ns.list()))
            
    def testRemoveProtected(self):
        ns=Pyro4.naming.NameServer()
        ns.register(Pyro4.constants.NAMESERVER_NAME, "PYRO:nameserver@host:555")
        self.assertEqual(0, ns.remove(Pyro4.constants.NAMESERVER_NAME))
        self.assertEqual(0, ns.remove(prefix="Pyro"))
        self.assertEqual(0, ns.remove(regex="Pyro.*"))
        self.assertTrue(Pyro4.constants.NAMESERVER_NAME in ns.list())

    def testUnicodeNames(self):
        ns=Pyro4.naming.NameServer()
        uri=Pyro4.core.URI("PYRO:unicode"+unichr(0x20ac)+"@host:5555")
        ns.register("unicodename"+unichr(0x20ac), uri)
        x=ns.lookup("unicodename"+unichr(0x20ac))
        self.assertEqual(uri, x)

    def testList(self):
        ns=Pyro4.naming.NameServer()
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
        self.assertRaises(NamingError, ns.list, regex="((((((broken")

    def testRefuseDotted(self):
        try:
            Pyro4.config.DOTTEDNAMES=True
            _=Pyro4.naming.NameServerDaemon(port=0)
            self.fail("should refuse to create name server")
        except PyroError:
            pass
        finally:
            Pyro4.config.DOTTEDNAMES=False
        
    def testNameserverWithStmt(self):
        ns=Pyro4.naming.NameServerDaemon(port=0)
        self.assertFalse(ns.nameserver is None)
        ns.close()
        self.assertTrue(ns.nameserver is None)
        with Pyro4.naming.NameServerDaemon(port=0) as ns:
            self.assertFalse(ns.nameserver is None)
            pass
        self.assertTrue(ns.nameserver is None)
        try:
            with Pyro4.naming.NameServerDaemon(port=0) as ns:
                self.assertFalse(ns.nameserver is None)
                print(1//0) # cause an error
            self.fail("expected error")
        except ZeroDivisionError: 
            pass
        self.assertTrue(ns.nameserver is None)
        ns=Pyro4.naming.NameServerDaemon(port=0)
        with ns:
            pass
        try:
            with ns:
                pass
            self.fail("expected error")
        except PyroError:
            # you cannot re-use a name server object in multiple with statements
            pass
        ns.close()

    def testStartNSfunc(self):
        myIpAddress=Pyro4.socketutil.getMyIpAddress(workaround127=True)
        uri1,ns1,bc1=Pyro4.naming.startNS(host=myIpAddress, port=0, enableBroadcast=False)
        uri2,ns2,bc2=Pyro4.naming.startNS(host=myIpAddress, port=0, enableBroadcast=True)
        self.assertTrue(isinstance(uri1, Pyro4.core.URI))
        self.assertTrue(isinstance(ns1, Pyro4.naming.NameServerDaemon))
        self.assertTrue(bc1 is None)
        self.assertTrue(isinstance(bc2, Pyro4.naming.BroadcastServer))
        sock=bc2.sock
        self.assertTrue(hasattr(sock,"fileno"))
        _=bc2.processRequest
        ns1.close()
        ns2.close()
        bc2.close()
    
    def testOwnloopBasics(self):
        myIpAddress=Pyro4.socketutil.getMyIpAddress(workaround127=True)
        uri1,ns1,bc1=Pyro4.naming.startNS(host=myIpAddress, port=0, enableBroadcast=True)
        self.assertTrue(bc1.fileno() > 0)
        if hasattr(select, "poll"):
            p=select.poll()
            if os.name=="java":
                # jython requires nonblocking sockets for poll
                ns1.sock.setblocking(False)
                bc1.sock.setblocking(False)
            for s in ns1.sockets:
                p.register(s, select.POLLIN)
            p.register(bc1.fileno(), select.POLLIN)
            p.poll(100)
            if hasattr(p,"close"):
                p.close()
        else:
            rs=[bc1]
            rs.extend(ns1.sockets)
            _,_,_=select.select(rs,[],[],0.1)
        ns1.close()
        bc1.close()

    def testNSmain(self):
        oldstdout=sys.stdout
        oldstderr=sys.stderr
        try:
            sys.stdout=StringIO()
            sys.stderr=StringIO()
            self.assertRaises(SystemExit, Pyro4.naming.main, ["--invalidarg"])
            self.assertTrue("no such option" in sys.stderr.getvalue())
            sys.stderr.truncate(0)
            sys.stdout.truncate(0)
            self.assertRaises(SystemExit, Pyro4.naming.main, ["-h"])
            self.assertTrue("show this help message" in sys.stdout.getvalue())
        finally:
            sys.stdout=oldstdout
            sys.stderr=oldstderr

    def testNSCmain(self):
        oldstdout=sys.stdout
        oldstderr=sys.stderr
        try:
            sys.stdout=StringIO()
            sys.stderr=StringIO()
            self.assertRaises(SystemExit, Pyro4.nsc.main, ["--invalidarg"])
            self.assertTrue("no such option" in sys.stderr.getvalue())
            sys.stderr.truncate(0)
            sys.stdout.truncate(0)
            self.assertRaises(SystemExit, Pyro4.nsc.main, ["-h"])
            self.assertTrue("show this help message" in sys.stdout.getvalue())
        finally:
            sys.stdout=oldstdout
            sys.stderr=oldstderr
            
    def testNSCfunctions(self):
        oldstdout=sys.stdout
        oldstderr=sys.stderr
        try:
            sys.stdout=StringIO()
            sys.stderr=StringIO()
            ns=Pyro4.naming.NameServer()
            Pyro4.nsc.handleCommand(ns, None, ["foo"])
            self.assertTrue(sys.stdout.getvalue().startswith("Error: KeyError "))
            Pyro4.nsc.handleCommand(ns, None, ["ping"])
            self.assertTrue(sys.stdout.getvalue().endswith("ping ok.\n"))
            Pyro4.nsc.handleCommand(ns, None, ["list"])
            self.assertTrue(sys.stdout.getvalue().endswith("END LIST \n"))
            Pyro4.nsc.handleCommand(ns, None, ["listmatching", "name.$"])
            self.assertTrue(sys.stdout.getvalue().endswith("END LIST - regex 'name.$'\n"))
            self.assertFalse("name1" in sys.stdout.getvalue())
            Pyro4.nsc.handleCommand(ns, None, ["register", "name1", "PYRO:obj1@hostname:9999"])
            self.assertTrue(sys.stdout.getvalue().endswith("Registered name1\n"))
            Pyro4.nsc.handleCommand(ns, None, ["remove", "name2"])
            self.assertTrue(sys.stdout.getvalue().endswith("Nothing removed\n"))
            Pyro4.nsc.handleCommand(ns, None, ["listmatching", "name.$"])
            self.assertTrue("name1 --> PYRO:obj1@hostname:9999" in sys.stdout.getvalue())
            #Pyro4.nsc.handleCommand(ns, None, ["removematching","name?"])
        finally:
            sys.stdout=oldstdout
            sys.stderr=oldstderr

    def testNAT(self):
        uri,ns,bc=Pyro4.naming.startNS(host="", port=0, enableBroadcast=True, nathost="nathosttest", natport=12345)
        self.assertEqual("nathosttest:12345", uri.location)
        self.assertEqual("nathosttest:12345", ns.uriFor("thing").location)
        self.assertNotEqual("nathosttest:12345", bc.nsUri.location, "broadcast location must not be the NAT location")
        ns.close()
        bc.close()


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
