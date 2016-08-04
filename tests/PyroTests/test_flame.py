"""
Tests for Pyro Flame.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import sys
import unittest
import Pyro4.utils.flame
import Pyro4.utils.flameserver
import Pyro4.core
import Pyro4.errors
import Pyro4.constants
from testsupport import *


class FlameDisabledTests(unittest.TestCase):
    def testFlameDisabled(self):
        with Pyro4.core.Daemon() as d:
            with self.assertRaises(Pyro4.errors.SecurityError) as ex:
                Pyro4.utils.flame.start(d)
            self.assertIn("disabled", str(ex.exception))   # default should be disabled even when pickle is activated

    def testRequirePickleExclusively(self):
        with Pyro4.core.Daemon() as d:
            Pyro4.config.FLAME_ENABLED = True
            sers = Pyro4.config.SERIALIZERS_ACCEPTED
            Pyro4.config.SERIALIZERS_ACCEPTED = {"json", "serpent", "marshal"}
            self.assertRaises(Pyro4.errors.SerializeError, Pyro4.utils.flame.start, d)  # require pickle
            Pyro4.config.SERIALIZERS_ACCEPTED.add("pickle")
            self.assertRaises(Pyro4.errors.SerializeError, Pyro4.utils.flame.start, d)  # require pickle exclusively
            Pyro4.config.SERIALIZERS_ACCEPTED = {"pickle"}
            Pyro4.utils.flame.start(d)
            Pyro4.config.SERIALIZERS_ACCEPTED = sers
            Pyro4.config.FLAME_ENABLED = False


class FlameTests(unittest.TestCase):
    def setUp(self):
        Pyro4.config.FLAME_ENABLED = True
        self._serializers = Pyro4.config.SERIALIZERS_ACCEPTED
        Pyro4.config.SERIALIZERS_ACCEPTED = {"pickle"}

    def tearDown(self):
        Pyro4.config.FLAME_ENABLED = False
        Pyro4.config.SERIALIZERS_ACCEPTED = self._serializers

    def testExposed(self):
        e = Pyro4.utils.flame.Flame()
        self.assertTrue(hasattr(e, "_pyroExposed"))

    def testCreateModule(self):
        module = Pyro4.utils.flame.createModule("testmodule", "def x(y): return y*y")
        self.assertEqual(9, module.x(3))
        module = Pyro4.utils.flame.createModule("testmodule2.submodule.subsub", "def x(y): return y*y")
        self.assertEqual(9, module.x(3))
        import testmodule2.submodule.subsub
        self.assertEqual(9, testmodule2.submodule.subsub.x(3))

    def testCreateModuleNamespace(self):
        namespace = {}
        Pyro4.utils.flame.createModule("testmodule2.submodule.subsub", "def x(y): return y*y", namespace=namespace)
        self.assertEqual(9, namespace["testmodule2"].submodule.subsub.x(3))

    def testExecFunction(self):
        namespace = {}
        Pyro4.utils.flame.exec_function("foobar=5+6", "<foo>", namespace)
        self.assertEqual(11, namespace["foobar"])

    def testExecFunctionNewlines(self):
        namespace = {}
        Pyro4.utils.flame.exec_function("if True:\r\n  foobar=5+6\r\n   ", "<foo>", namespace)
        self.assertEqual(11, namespace["foobar"])

    def testFlameModule(self):
        with Pyro4.core.Daemon() as d:
            Pyro4.utils.flame.start(d)
            flameserver = d.objectsById[Pyro4.constants.FLAME_NAME]
            with Pyro4.utils.flame.FlameModule(flameserver, "sys") as m:
                self.assertIn("module 'sys' at", str(m))
                self.assertIsInstance(m.exc_info, Pyro4.core._RemoteMethod)

    def testFlameBuiltin(self):
        with Pyro4.core.Daemon() as d:
            Pyro4.utils.flame.start(d)
            flameserver = d.objectsById[Pyro4.constants.FLAME_NAME]
            with Pyro4.utils.flame.FlameBuiltin(flameserver, "max") as builtin:
                self.assertTrue(hasattr(builtin, "__call__"))
                self.assertIn("builtin 'max' at", str(builtin))

    def testFlameserverMain(self):
        oldstdout = sys.stdout
        oldstderr = sys.stderr
        try:
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            self.assertRaises(SystemExit, Pyro4.utils.flameserver.main, ["--invalidarg"])
            self.assertTrue("no such option" in sys.stderr.getvalue())
            sys.stderr.truncate(0)
            sys.stdout.truncate(0)
            self.assertRaises(SystemExit, Pyro4.utils.flameserver.main, ["-h"])
            self.assertTrue("show this help message" in sys.stdout.getvalue())
        finally:
            sys.stdout = oldstdout
            sys.stderr = oldstderr


if __name__ == "__main__":
    # import sys; sys.argv = ['', 'Test.testName']
    unittest.main()
