"""
Tests for the name server (online/running).

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import time
import unittest
import Pyro4.core
import Pyro4.naming
import Pyro4.socketutil
import Pyro4.constants
from Pyro4.errors import CommunicationError, NamingError
from Pyro4 import threadutil


class NSLoopThread(threadutil.Thread):
    def __init__(self, nameserver):
        super(NSLoopThread, self).__init__()
        self.setDaemon(True)
        self.nameserver = nameserver
        self.running = threadutil.Event()
        self.running.clear()

    def run(self):
        self.running.set()
        try:
            self.nameserver.requestLoop()
        except CommunicationError:
            pass  # ignore pyro communication errors


class BCSetupTests(unittest.TestCase):
    def testBCstart(self):
        myIpAddress = Pyro4.socketutil.getIpAddress("", workaround127=True)
        nsUri, nameserver, bcserver = Pyro4.naming.startNS(host=myIpAddress, port=0, bcport=0, enableBroadcast=False)
        self.assertIsNone(bcserver)
        nameserver.close()
        nsUri, nameserver, bcserver = Pyro4.naming.startNS(host=myIpAddress, port=0, bcport=0, enableBroadcast=True)
        self.assertIsNotNone(bcserver, "expected a BC server to be running. Check DNS setup (hostname must not resolve to loopback address")
        self.assertGreater(bcserver.fileno(), 1)
        self.assertIsNotNone(bcserver.sock)
        nameserver.close()
        bcserver.close()


class NameServerTests(unittest.TestCase):
    def setUp(self):
        Pyro4.config.POLLTIMEOUT = 0.1
        myIpAddress = Pyro4.socketutil.getIpAddress("", workaround127=True)
        self.nsUri, self.nameserver, self.bcserver = Pyro4.naming.startNS(host=myIpAddress, port=0, bcport=0)
        self.assertIsNotNone(self.bcserver, "expected a BC server to be running")
        self.bcserver.runInThread()
        self.daemonthread = NSLoopThread(self.nameserver)
        self.daemonthread.start()
        self.daemonthread.running.wait()
        time.sleep(0.05)
        self.old_bcPort = Pyro4.config.NS_BCPORT
        self.old_nsPort = Pyro4.config.NS_PORT
        self.old_nsHost = Pyro4.config.NS_HOST
        Pyro4.config.NS_PORT = self.nsUri.port
        Pyro4.config.NS_HOST = myIpAddress
        Pyro4.config.NS_BCPORT = self.bcserver.getPort()

    def tearDown(self):
        time.sleep(0.01)
        self.nameserver.shutdown()
        self.bcserver.close()
        self.daemonthread.join()
        Pyro4.config.NS_HOST = self.old_nsHost
        Pyro4.config.NS_PORT = self.old_nsPort
        Pyro4.config.NS_BCPORT = self.old_bcPort

    def testLookupUnixsockParsing(self):
        # this must not raise AttributeError, it did before because of a parse bug
        with self.assertRaises(NamingError):
            Pyro4.naming.locateNS("./u:/tmp/pyro4-naming.usock")

    def testLookupAndRegister(self):
        ns = Pyro4.naming.locateNS()  # broadcast lookup
        self.assertIsInstance(ns, Pyro4.core.Proxy)
        ns._pyroRelease()
        ns = Pyro4.naming.locateNS(self.nsUri.host)  # normal lookup
        self.assertIsInstance(ns, Pyro4.core.Proxy)
        uri = ns._pyroUri
        self.assertEqual("PYRO", uri.protocol)
        self.assertEqual(self.nsUri.host, uri.host)
        self.assertEqual(Pyro4.config.NS_PORT, uri.port)
        self.assertIsNone(ns._pyroHmacKey)
        ns._pyroRelease()
        ns = Pyro4.naming.locateNS(self.nsUri.host, Pyro4.config.NS_PORT, hmac_key=None)
        uri = ns._pyroUri
        self.assertEqual("PYRO", uri.protocol)
        self.assertEqual(self.nsUri.host, uri.host)
        self.assertEqual(Pyro4.config.NS_PORT, uri.port)
        self.assertIsNone(ns._pyroHmacKey)
        # check that we cannot register a stupid type
        self.assertRaises(TypeError, ns.register, "unittest.object1", 5555)
        # we can register str or URI, lookup always returns URI
        ns.register("unittest.object2", "PYRO:55555@host.com:4444")
        self.assertEqual(Pyro4.core.URI("PYRO:55555@host.com:4444"), ns.lookup("unittest.object2"))
        ns.register("unittest.object3", Pyro4.core.URI("PYRO:66666@host.com:4444"))
        self.assertEqual(Pyro4.core.URI("PYRO:66666@host.com:4444"), ns.lookup("unittest.object3"))
        ns._pyroRelease()

    def testLookupInvalidHmac(self):
        with self.assertRaises(NamingError):
            Pyro4.naming.locateNS(self.nsUri.host, Pyro4.config.NS_PORT, hmac_key="invalidkey")

    def testDaemonPyroObj(self):
        uri = self.nsUri
        uri.object = Pyro4.constants.DAEMON_NAME
        with Pyro4.core.Proxy(uri) as daemonobj:
            daemonobj.ping()
            daemonobj.registered()
            try:
                daemonobj.shutdown()
                self.fail("should not succeed to call unexposed method on daemon")
            except AttributeError:
                pass

    def testMulti(self):
        uristr = str(self.nsUri)
        p = Pyro4.core.Proxy(uristr)
        p._pyroBind()
        p._pyroRelease()
        uri = Pyro4.naming.resolve(uristr)
        p = Pyro4.core.Proxy(uri)
        p._pyroBind()
        p._pyroRelease()
        uri = Pyro4.naming.resolve(uristr)
        p = Pyro4.core.Proxy(uri)
        p._pyroBind()
        p._pyroRelease()
        uri = Pyro4.naming.resolve(uristr)
        p = Pyro4.core.Proxy(uri)
        p._pyroBind()
        p._pyroRelease()
        uri = Pyro4.naming.resolve(uristr)
        p = Pyro4.core.Proxy(uri)
        p._pyroBind()
        p._pyroRelease()
        uri = Pyro4.naming.resolve(uristr)
        p = Pyro4.core.Proxy(uri)
        p._pyroBind()
        p._pyroRelease()
        daemonUri = "PYRO:" + Pyro4.constants.DAEMON_NAME + "@" + uri.location
        _ = Pyro4.naming.resolve(daemonUri)
        _ = Pyro4.naming.resolve(daemonUri)
        _ = Pyro4.naming.resolve(daemonUri)
        _ = Pyro4.naming.resolve(daemonUri)
        _ = Pyro4.naming.resolve(daemonUri)
        _ = Pyro4.naming.resolve(daemonUri)
        uri = Pyro4.naming.resolve(daemonUri)
        pyronameUri = "PYRONAME:" + Pyro4.constants.NAMESERVER_NAME + "@" + uri.location
        _ = Pyro4.naming.resolve(pyronameUri)
        _ = Pyro4.naming.resolve(pyronameUri)
        _ = Pyro4.naming.resolve(pyronameUri)
        _ = Pyro4.naming.resolve(pyronameUri)
        _ = Pyro4.naming.resolve(pyronameUri)
        _ = Pyro4.naming.resolve(pyronameUri)

    def testResolve(self):
        resolved1 = Pyro4.naming.resolve(Pyro4.core.URI("PYRO:12345@host.com:4444"), hmac_key=None)
        resolved2 = Pyro4.naming.resolve("PYRO:12345@host.com:4444", hmac_key=None)
        self.assertTrue(type(resolved1) is Pyro4.core.URI)
        self.assertEqual(resolved1, resolved2)
        self.assertEqual("PYRO:12345@host.com:4444", str(resolved1))

        ns = Pyro4.naming.locateNS(self.nsUri.host, self.nsUri.port)
        host = "[" + self.nsUri.host + "]" if ":" in self.nsUri.host else self.nsUri.host
        uri = Pyro4.naming.resolve("PYRONAME:" + Pyro4.constants.NAMESERVER_NAME + "@" + host + ":" + str(self.nsUri.port))
        self.assertEqual("PYRO", uri.protocol)
        self.assertEqual(self.nsUri.host, uri.host)
        self.assertEqual(Pyro4.constants.NAMESERVER_NAME, uri.object)
        self.assertEqual(uri, ns._pyroUri)
        ns._pyroRelease()

        # broadcast lookup
        self.assertRaises(NamingError, Pyro4.naming.resolve, "PYRONAME:unknown_object")
        uri = Pyro4.naming.resolve("PYRONAME:" + Pyro4.constants.NAMESERVER_NAME)
        self.assertEqual(Pyro4.core.URI, type(uri))
        self.assertEqual("PYRO", uri.protocol)

        # test some errors
        self.assertRaises(NamingError, Pyro4.naming.resolve, "PYRONAME:unknown_object@" + host)
        self.assertRaises(TypeError, Pyro4.naming.resolve, 999)  # wrong arg type

    def testRefuseDottedNames(self):
        old_metadata = Pyro4.config.METADATA
        Pyro4.config.METADATA = False
        with Pyro4.naming.locateNS(self.nsUri.host, self.nsUri.port) as ns:
            # the name server should never have dotted names enabled
            self.assertRaises(AttributeError, ns.namespace.keys)
            self.assertIsNotNone(ns._pyroConnection)
        self.assertIsNone(ns._pyroConnection)
        Pyro4.config.METADATA = old_metadata


class NameServerTests0000(unittest.TestCase):
    def setUp(self):
        Pyro4.config.POLLTIMEOUT = 0.1
        self.nsUri, self.nameserver, self.bcserver = Pyro4.naming.startNS(host="", port=0, bcport=0)
        host_check = self.nsUri.host
        self.assertEqual("0.0.0.0", host_check, "for hostname \"\" the resulting ip must be 0.0.0.0 (or ipv6 equivalent)")
        self.assertIsNotNone(self.bcserver, "expected a BC server to be running")
        self.bcserver.runInThread()
        self.old_bcPort = Pyro4.config.NS_BCPORT
        self.old_nsPort = Pyro4.config.NS_PORT
        self.old_nsHost = Pyro4.config.NS_HOST
        Pyro4.config.NS_PORT = self.nsUri.port
        Pyro4.config.NS_HOST = self.nsUri.host
        Pyro4.config.NS_BCPORT = self.bcserver.getPort()

    def tearDown(self):
        time.sleep(0.01)
        self.nameserver.shutdown()
        self.bcserver.close()
        Pyro4.config.NS_HOST = self.old_nsHost
        Pyro4.config.NS_PORT = self.old_nsPort
        Pyro4.config.NS_BCPORT = self.old_bcPort

    def testBCLookup0000(self):
        ns = Pyro4.naming.locateNS()  # broadcast lookup
        self.assertIsInstance(ns, Pyro4.core.Proxy)
        self.assertNotEqual("0.0.0.0", ns._pyroUri.host, "returned location must not be 0.0.0.0 when running on 0.0.0.0")
        ns._pyroRelease()


class NameServerTestsHmac(unittest.TestCase):
    def setUp(self):
        Pyro4.config.POLLTIMEOUT = 0.1
        myIpAddress = Pyro4.socketutil.getIpAddress("", workaround127=True)
        self.nsUri, self.nameserver, self.bcserver = Pyro4.naming.startNS(host=myIpAddress, port=0, bcport=0, hmac=b"test_key")
        self.assertIsNotNone(self.bcserver, "expected a BC server to be running")
        self.bcserver.runInThread()
        self.daemonthread = NSLoopThread(self.nameserver)
        self.daemonthread.start()
        self.daemonthread.running.wait()
        time.sleep(0.05)
        self.old_bcPort = Pyro4.config.NS_BCPORT
        self.old_nsPort = Pyro4.config.NS_PORT
        self.old_nsHost = Pyro4.config.NS_HOST
        Pyro4.config.NS_PORT = self.nsUri.port
        Pyro4.config.NS_HOST = myIpAddress
        Pyro4.config.NS_BCPORT = self.bcserver.getPort()

    def tearDown(self):
        time.sleep(0.01)
        self.nameserver.shutdown()
        self.bcserver.close()
        self.daemonthread.join()
        Pyro4.config.NS_HOST = self.old_nsHost
        Pyro4.config.NS_PORT = self.old_nsPort
        Pyro4.config.NS_BCPORT = self.old_bcPort

    def testLookupAndRegister(self):
        ns = Pyro4.naming.locateNS()  # broadcast lookup without providing hmac still works
        self.assertIsInstance(ns, Pyro4.core.Proxy)
        self.assertIsNone(ns._pyroHmacKey)   #... but no hmac is set on the proxy
        ns._pyroRelease()
        ns = Pyro4.naming.locateNS(hmac_key=b"test_key")  # broadcast lookup providing hmac
        self.assertIsInstance(ns, Pyro4.core.Proxy)
        self.assertEqual(b"test_key", ns._pyroHmacKey)  # ... sets the hmac on the proxy
        ns._pyroRelease()
        ns = Pyro4.naming.locateNS(self.nsUri.host, Pyro4.config.NS_PORT, hmac_key=b"test_key")
        uri = ns._pyroUri
        self.assertEqual("PYRO", uri.protocol)
        self.assertEqual(self.nsUri.host, uri.host)
        self.assertEqual(Pyro4.config.NS_PORT, uri.port)
        self.assertEqual(b"test_key", ns._pyroHmacKey)
        ns._pyroRelease()

    def testResolve(self):
        uri = Pyro4.naming.resolve("PYRONAME:Pyro.NameServer", hmac_key=b"test_key")
        self.assertEqual("PYRO", uri.protocol)
        self.assertEqual(self.nsUri.host, uri.host)
        self.assertEqual(Pyro4.config.NS_PORT, uri.port)

    def testPyroname(self):
        with Pyro4.Proxy("PYRONAME:Pyro.NameServer") as p:
            p._pyroHmacKey = b"test_key"
            p.ping()   # the resolve() that is done should also use the hmac key

    def testResolveWrongKey(self):
        with self.assertRaises(CommunicationError) as ex:
            ns = Pyro4.naming.resolve("PYRONAME:Pyro.NameServer", hmac_key=b"wrong_key")
        self.assertEqual("cannot connect: message hmac mismatch", str(ex.exception))


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
