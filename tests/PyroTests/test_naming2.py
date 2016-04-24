"""
Tests for the name server (offline/basic logic).

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement, print_function
import sys
import os
import unittest
import Pyro4.core
import Pyro4.naming
import Pyro4.naming_storage
import Pyro4.nsc
import Pyro4.constants
import Pyro4.socketutil
from Pyro4.errors import NamingError, PyroError
from testsupport import *


class OfflineNameServerTests(unittest.TestCase):
    def setUp(self):
        self.storageProvider = Pyro4.naming.MemoryStorage()

    def tearDown(self):
        self.storageProvider.clear()
        self.storageProvider.close()

    def testRegister(self):
        ns = Pyro4.naming.NameServer(storageProvider=self.storageProvider)
        self.storageProvider.clear()
        ns.ping()
        ns.register("test.object1", "PYRO:000000@host.com:4444")
        ns.register("test.object2", "PYRO:222222@host.com:4444")
        ns.register("test.object3", "PYRO:333333@host.com:4444")
        self.assertEqual("PYRO:000000@host.com:4444", str(ns.lookup("test.object1")))
        ns.register("test.object1", "PYRO:111111@host.com:4444")  # registering again should be ok by default
        self.assertEqual("PYRO:111111@host.com:4444", str(ns.lookup("test.object1")), "should be new uri")
        ns.register("test.sub.objectA", Pyro4.core.URI("PYRO:AAAAAA@host.com:4444"))
        ns.register("test.sub.objectB", Pyro4.core.URI("PYRO:BBBBBB@host.com:4444"))

        # if safe=True, a registration of an existing name should give a NamingError
        self.assertRaises(NamingError, ns.register, "test.object1", "PYRO:X@Y:5555", safe=True)

        self.assertRaises(TypeError, ns.register, None, None)
        self.assertRaises(TypeError, ns.register, 4444, 4444)
        self.assertRaises(TypeError, ns.register, "test.wrongtype", 4444)
        self.assertRaises(TypeError, ns.register, 4444, "PYRO:X@Y:5555")

        self.assertRaises(NamingError, ns.lookup, "unknown_object")

        uri = ns.lookup("test.object3")
        self.assertEqual(Pyro4.core.URI("PYRO:333333@host.com:4444"), uri)  # lookup always returns URI
        ns.remove("unknown_object")
        ns.remove("test.object1")
        ns.remove("test.object2")
        ns.remove("test.object3")
        all_objs = ns.list()
        self.assertEqual(2, len(all_objs))  # 2 leftover objects
        self.assertRaises(PyroError, ns.register, "test.nonurivalue", "THISVALUEISNOTANURI")
        ns.storage.close()

    def testRemove(self):
        ns = Pyro4.naming.NameServer(storageProvider=self.storageProvider)
        self.storageProvider.clear()
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
        ns.storage.close()

    def testRemoveProtected(self):
        ns = Pyro4.naming.NameServer(storageProvider=self.storageProvider)
        self.storageProvider.clear()
        ns.register(Pyro4.constants.NAMESERVER_NAME, "PYRO:nameserver@host:555")
        self.assertEqual(0, ns.remove(Pyro4.constants.NAMESERVER_NAME))
        self.assertEqual(0, ns.remove(prefix="Pyro"))
        self.assertEqual(0, ns.remove(regex="Pyro.*"))
        self.assertIn(Pyro4.constants.NAMESERVER_NAME, ns.list())
        ns.storage.close()

    @unittest.skipIf(sys.platform == "cli", "ironpython has a bug in anydbm/whichdb when inserting unicode keys")   # see https://github.com/IronLanguages/main/issues/1165
    def testUnicodeNames(self):
        ns = Pyro4.naming.NameServer(storageProvider=self.storageProvider)
        self.storageProvider.clear()
        uri = Pyro4.core.URI("PYRO:unicode" + unichr(0x20ac) + "@host:5555")
        ns.register("unicodename" + unichr(0x20ac), uri)
        x = ns.lookup("unicodename" + unichr(0x20ac))
        self.assertEqual(uri, x)
        ns.storage.close()

    def testList(self):
        ns = Pyro4.naming.NameServer(storageProvider=self.storageProvider)
        self.storageProvider.clear()
        ns.register("test.objects.1", "PYRONAME:something1")
        ns.register("test.objects.2", "PYRONAME:something2")
        ns.register("test.objects.3", "PYRONAME:something3")
        ns.register("test.other.a", "PYRONAME:somethingA")
        ns.register("test.other.b", "PYRONAME:somethingB")
        ns.register("test.other.c", "PYRONAME:somethingC")
        ns.register("entirely.else", "PYRONAME:meh")
        objects = ns.list()
        self.assertEqual(7, len(objects))
        objects = ns.list(prefix="nothing")
        self.assertEqual(0, len(objects))
        objects = ns.list(prefix="test.")
        self.assertEqual(6, len(objects))
        objects = ns.list(regex=r".+other..")
        self.assertEqual(3, len(objects))
        self.assertIn("test.other.a", objects)
        self.assertEqual("PYRONAME:somethingA", objects["test.other.a"])
        objects = ns.list(regex=r"\d\d\d\d\d\d\d\d\d\d")
        self.assertEqual(0, len(objects))
        self.assertRaises(NamingError, ns.list, regex="((((((broken")
        ns.storage.close()

    def testNameserverWithStmt(self):
        ns = Pyro4.naming.NameServerDaemon(port=0)
        self.assertIsNotNone(ns.nameserver)
        ns.close()
        self.assertIsNone(ns.nameserver)
        with Pyro4.naming.NameServerDaemon(port=0) as ns:
            self.assertIsNotNone(ns.nameserver)
            pass
        self.assertIsNone(ns.nameserver)
        try:
            with Pyro4.naming.NameServerDaemon(port=0) as ns:
                self.assertIsNotNone(ns.nameserver)
                print(1 // 0)  # cause an error
            self.fail("expected error")
        except ZeroDivisionError:
            pass
        self.assertIsNone(ns.nameserver)
        ns = Pyro4.naming.NameServerDaemon(port=0)
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
        myIpAddress = Pyro4.socketutil.getIpAddress("", workaround127=True)
        uri1, ns1, bc1 = Pyro4.naming.startNS(host=myIpAddress, port=0, bcport=0, enableBroadcast=False)
        uri2, ns2, bc2 = Pyro4.naming.startNS(host=myIpAddress, port=0, bcport=0, enableBroadcast=True)
        self.assertIsInstance(uri1, Pyro4.core.URI)
        self.assertIsInstance(ns1, Pyro4.naming.NameServerDaemon)
        self.assertIsNone(bc1)
        self.assertIsInstance(bc2, Pyro4.naming.BroadcastServer)
        sock = bc2.sock
        self.assertTrue(hasattr(sock, "fileno"))
        _ = bc2.processRequest
        ns1.close()
        ns2.close()
        bc2.close()

    def testNSmain(self):
        oldstdout = sys.stdout
        oldstderr = sys.stderr
        try:
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            self.assertRaises(SystemExit, Pyro4.naming.main, ["--invalidarg"])
            self.assertTrue("no such option" in sys.stderr.getvalue())
            sys.stderr.truncate(0)
            sys.stdout.truncate(0)
            self.assertRaises(SystemExit, Pyro4.naming.main, ["-h"])
            self.assertTrue("show this help message" in sys.stdout.getvalue())
        finally:
            sys.stdout = oldstdout
            sys.stderr = oldstderr

    def testNSCmain(self):
        oldstdout = sys.stdout
        oldstderr = sys.stderr
        try:
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            self.assertRaises(SystemExit, Pyro4.nsc.main, ["--invalidarg"])
            self.assertTrue("no such option" in sys.stderr.getvalue())
            sys.stderr.truncate(0)
            sys.stdout.truncate(0)
            self.assertRaises(SystemExit, Pyro4.nsc.main, ["-h"])
            self.assertTrue("show this help message" in sys.stdout.getvalue())
        finally:
            sys.stdout = oldstdout
            sys.stderr = oldstderr

    def testNSCfunctions(self):
        oldstdout = sys.stdout
        try:
            sys.stdout = StringIO()
            ns = Pyro4.naming.NameServer(storageProvider=self.storageProvider)
            Pyro4.nsc.handleCommand(ns, None, ["foo"])
            self.assertTrue(sys.stdout.getvalue().startswith("Error: KeyError "))
            Pyro4.nsc.handleCommand(ns, None, ["ping"])
            self.assertTrue(sys.stdout.getvalue().endswith("ping ok.\n"))
            Pyro4.nsc.handleCommand(ns, None, ["lookup", "WeirdName"])
            self.assertTrue(sys.stdout.getvalue().endswith("Error: NamingError - unknown name: WeirdName\n"))
            Pyro4.nsc.handleCommand(ns, None, ["list"])
            self.assertTrue(sys.stdout.getvalue().endswith("END LIST \n"))
            Pyro4.nsc.handleCommand(ns, None, ["listmatching", "name.$"])
            self.assertTrue(sys.stdout.getvalue().endswith("END LIST - regex 'name.$'\n"))
            self.assertNotIn("name1", sys.stdout.getvalue())
            Pyro4.nsc.handleCommand(ns, None, ["register", "name1", "PYRO:obj1@hostname:9999"])
            self.assertTrue(sys.stdout.getvalue().endswith("Registered name1\n"))
            Pyro4.nsc.handleCommand(ns, None, ["remove", "name2"])
            self.assertTrue(sys.stdout.getvalue().endswith("Nothing removed\n"))
            Pyro4.nsc.handleCommand(ns, None, ["listmatching", "name.$"])
            self.assertIn("name1 --> PYRO:obj1@hostname:9999", sys.stdout.getvalue())
            # Pyro4.nsc.handleCommand(ns, None, ["removematching", "name.?"])  #  can't be tested, required user input
        finally:
            sys.stdout = oldstdout
            ns.storage.close()

    def testNAT(self):
        uri, ns, bc = Pyro4.naming.startNS(host="", port=0, enableBroadcast=True, nathost="nathosttest", natport=12345)
        self.assertEqual("nathosttest:12345", uri.location)
        self.assertEqual("nathosttest:12345", ns.uriFor("thing").location)
        self.assertNotEqual("nathosttest:12345", bc.nsUri.location, "broadcast location must not be the NAT location")
        ns.close()
        bc.close()

    def testMetadataRegisterInvalidTypes(self):
        ns = Pyro4.naming.NameServer(storageProvider=self.storageProvider)
        with self.assertRaises(TypeError):
            ns.register("meta1", "PYRO:meta1@localhost:1111", metadata=12345)   # metadata must be iterable
        with self.assertRaises(TypeError):
            ns.register("meta1", "PYRO:meta1@localhost:1111", metadata="string")   # metadata must not be str

    def testMetadataListInvalidTypes(self):
        ns = Pyro4.naming.NameServer(storageProvider=self.storageProvider)
        with self.assertRaises(TypeError):
            ns.list(metadata_all=12345)
        with self.assertRaises(TypeError):
            ns.list(metadata_all="string")
        with self.assertRaises(TypeError):
            ns.list(metadata_any=12345)
        with self.assertRaises(TypeError):
            ns.list(metadata_any="string")

    def testMetadata(self):
        self.storageProvider.clear()
        ns = Pyro4.naming.NameServer(storageProvider=self.storageProvider)
        # register some names with metadata, and perform simple lookups
        ns.register("meta1", "PYRO:meta1@localhost:1111", metadata={"a", "b", "c"})
        ns.register("meta2", "PYRO:meta2@localhost:2222", metadata={"x", "y", "z"})
        ns.register("meta3", "PYRO:meta3@localhost:3333", metadata=["p", "q", "r", "r", "q"])
        uri = ns.lookup("meta1")
        self.assertEqual("meta1", uri.object)
        uri, metadata = ns.lookup("meta1", return_metadata=True)
        self.assertEqual("meta1", uri.object)
        self.assertSetEqual({"a", "b", "c"}, set(metadata))
        uri = ns.lookup("meta2")
        self.assertEqual("meta2", uri.object)
        uri, metadata = ns.lookup("meta2", return_metadata=True)
        self.assertEqual("meta2", uri.object)
        self.assertSetEqual({"x", "y", "z"}, set(metadata))
        uri, metadata = ns.lookup("meta3", return_metadata=True)
        self.assertEqual("meta3", uri.object)
        self.assertIsInstance(metadata, list)
        self.assertSetEqual({"p", "q", "r"}, set(metadata))
        # get a list of everything, without and with metadata
        reg = ns.list()
        self.assertDictEqual({'meta1': 'PYRO:meta1@localhost:1111', 'meta2': 'PYRO:meta2@localhost:2222',
                              'meta3': 'PYRO:meta3@localhost:3333'}, reg)
        reg = ns.list(return_metadata=True)
        uri1, meta1 = reg["meta1"]
        uri2, meta2 = reg["meta2"]
        self.assertEqual("PYRO:meta1@localhost:1111", uri1)
        self.assertSetEqual({"a", "b", "c"}, set(meta1))
        self.assertEqual("PYRO:meta2@localhost:2222", uri2)
        self.assertSetEqual({"x", "y", "z"}, set(meta2))
        # filter on metadata subset
        reg = ns.list(metadata_all={"a", "c"}, return_metadata=False)
        self.assertEqual(1, len(reg))
        self.assertEqual("PYRO:meta1@localhost:1111", reg["meta1"])
        reg = ns.list(metadata_all={"a", "c"}, return_metadata=True)
        self.assertEqual(1, len(reg))
        uri1, meta1 = reg["meta1"]
        self.assertEqual("PYRO:meta1@localhost:1111", uri1)
        self.assertSetEqual({"a", "b", "c"}, set(meta1))
        reg = ns.list(metadata_all={"a", "wrong"})
        self.assertEqual({}, reg)
        reg = ns.list(metadata_all={"a", "b", "c", "wrong"})
        self.assertEqual({}, reg)
        reg = ns.list(metadata_all={"a", "c", "x"})
        self.assertEqual({}, reg)
        # update some metadata
        with self.assertRaises(NamingError):
            ns.set_metadata("notexistingname", set())
        ns.set_metadata("meta1", {"one", "two", "three"})
        uri, meta = ns.lookup("meta1", return_metadata=True)
        self.assertSetEqual({"one", "two", "three"}, set(meta))
        # check that a collection is converted to a set
        ns.set_metadata("meta1", ["one", "two", "three", "three", "two"])
        uri, meta = ns.lookup("meta1", return_metadata=True)
        self.assertIsInstance(meta, list)
        self.assertSetEqual({"one", "two", "three"}, set(meta))
        # remove record that has some metadata
        ns.remove("meta1")
        ns.remove("meta3")
        self.assertEqual(["meta2"], list(ns.list().keys()))
        # other list filters
        reg = ns.list(prefix="meta", return_metadata=True)
        self.assertEqual(1, len(reg))
        self.assertSetEqual({"x", "y", "z"}, set(reg["meta2"][1]))
        reg = ns.list(regex="meta2.*", return_metadata=True)
        self.assertEqual(1, len(reg))
        self.assertSetEqual({"x", "y", "z"}, set(reg["meta2"][1]))
        self.assertEqual(1, ns.count())

    def testMetadataAny(self):
        self.storageProvider.clear()
        ns = Pyro4.naming.NameServer(storageProvider=self.storageProvider)
        # register some names with metadata, and perform simple lookups
        ns.register("meta1", "PYRO:meta1@localhost:1111", metadata={"a", "b", "c"})
        ns.register("meta2", "PYRO:meta2@localhost:2222", metadata={"x", "y", "z"})
        ns.register("meta3", "PYRO:meta3@localhost:2222", metadata={"k", "l", "m"})
        result = ns.list(metadata_any={"1", "2", "3"})
        self.assertEqual({}, result)
        result = ns.list(metadata_any={"1", "2", "a"})
        self.assertEqual(1, len(result))
        self.assertIn("meta1", result)
        result = ns.list(metadata_any={"1", "2", "a", "z"})
        self.assertEqual(2, len(result))
        self.assertIn("meta1", result)
        self.assertIn("meta2", result)

    def testEmptyMetadata(self):
        self.storageProvider.clear()
        ns = Pyro4.naming.NameServer(storageProvider=self.storageProvider)
        # register some names with metadata, and perform simple lookups
        ns.register("meta1", "PYRO:meta1@localhost:1111", metadata=[])
        uri, meta = ns.lookup("meta1", return_metadata=True)
        self.assertEqual([], meta)
        registrations = ns.list(return_metadata=True)
        for name in registrations:
            uri, meta = registrations[name]
            self.assertEqual([], meta)
        ns.set_metadata("meta1", [])

    def testListNoMultipleFilters(self):
        ns = Pyro4.naming.NameServer(storageProvider=self.storageProvider)
        with self.assertRaises(ValueError):
            ns.list(prefix="a", regex="a")
        with self.assertRaises(ValueError):
            ns.list(prefix="a", metadata_all=[])


@unittest.skipIf(Pyro4.naming_storage.dbm is None, "dbm must be available")
class OfflineNameServerTestsDbmStorage(OfflineNameServerTests):
    def setUp(self):
        super(OfflineNameServerTestsDbmStorage, self).setUp()
        import glob
        for file in glob.glob("pyro-test.dbm*"):
            os.remove(file)
        self.storageProvider = Pyro4.naming_storage.DbmStorage("pyro-test.dbm")

    def tearDown(self):
        super(OfflineNameServerTestsDbmStorage, self).tearDown()
        import glob
        for file in glob.glob("pyro-test.dbm*"):
            os.remove(file)

    @unittest.skip("dbmstorage doesn't support metadata")
    def testMetadata(self):
        pass

    @unittest.skip("dbmstorage doesn't support metadata")
    def testMetadataAny(self):
        pass


@unittest.skipIf(Pyro4.naming_storage.sqlite3 is None, "sqlite3 must be available")
class OfflineNameServerTestsSqlStorage(OfflineNameServerTests):
    def setUp(self):
        super(OfflineNameServerTestsSqlStorage, self).setUp()
        self.storageProvider = Pyro4.naming_storage.SqlStorage("pyro-test.sqlite")

    def tearDown(self):
        super(OfflineNameServerTestsSqlStorage, self).tearDown()
        import glob
        for file in glob.glob("pyro-test.sqlite*"):
           os.remove(file)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
