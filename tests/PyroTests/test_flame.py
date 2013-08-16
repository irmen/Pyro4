"""
Tests for Pyro Flame.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import Pyro4.utils.flame
import Pyro4.utils.flameserver
import Pyro4.errors
from testsupport import *


class FlameDisabledTests(unittest.TestCase):
    def testFlameDisabled(self):
        with Pyro4.core.Daemon() as d:
            self.assertRaises(Pyro4.errors.SecurityError, Pyro4.utils.flame.start, d)   # default should be disabled
    def testRequirePickle(self):
        with Pyro4.core.Daemon() as d:
            Pyro4.config.FLAME_ENABLED=True
            Pyro4.config.SERIALIZERS_ACCEPTED.discard("pickle")
            self.assertRaises(RuntimeError, Pyro4.utils.flame.start, d)   # require pickle
            Pyro4.config.SERIALIZERS_ACCEPTED.add("pickle")
            Pyro4.utils.flame.start(d)
            Pyro4.config.SERIALIZERS_ACCEPTED.discard("pickle")


class FlameTests(unittest.TestCase):
    
    def setUp(self):
        Pyro4.config.HMAC_KEY=b"testsuite"
        Pyro4.config.FLAME_ENABLED=True
        Pyro4.config.SERIALIZERS_ACCEPTED.add("pickle")
    def tearDown(self):
        Pyro4.config.HMAC_KEY=None
        Pyro4.config.FLAME_ENABLED=False
        Pyro4.config.SERIALIZERS_ACCEPTED.discard("pickle")

    def testCreateModule(self):
        module=Pyro4.utils.flame.createModule("testmodule", "def x(y): return y*y")
        self.assertEqual(9, module.x(3))
        module=Pyro4.utils.flame.createModule("testmodule2.submodule.subsub", "def x(y): return y*y")
        self.assertEqual(9, module.x(3))
        import testmodule2.submodule.subsub
        self.assertEqual(9, testmodule2.submodule.subsub.x(3))

    def testCreateModuleNamespace(self):
        namespace={}
        Pyro4.utils.flame.createModule("testmodule2.submodule.subsub", "def x(y): return y*y", namespace=namespace)
        self.assertEqual(9, namespace["testmodule2"].submodule.subsub.x(3))

    def testExecFunction(self):
        namespace={}
        Pyro4.utils.flame.exec_function("foobar=5+6", "<foo>", namespace)
        self.assertEqual(11, namespace["foobar"])

    def testExecFunctionNewlines(self):
        namespace={}
        Pyro4.utils.flame.exec_function("if True:\r\n  foobar=5+6\r\n   ", "<foo>", namespace)
        self.assertEqual(11, namespace["foobar"])

    def testFlameModule(self):
        with Pyro4.core.Daemon() as d:
            Pyro4.utils.flame.start(d)
            flameserver=d.objectsById[Pyro4.constants.FLAME_NAME]
            with Pyro4.utils.flame.FlameModule(flameserver, "sys") as m:
                self.assertTrue("module 'sys' at" in str(m))
                self.assertTrue(isinstance(m.exc_info , Pyro4.core._RemoteMethod))

    def testFlameBuiltin(self):
        with Pyro4.core.Daemon() as d:
            Pyro4.utils.flame.start(d)
            flameserver=d.objectsById[Pyro4.constants.FLAME_NAME]
            with Pyro4.utils.flame.FlameBuiltin(flameserver, "max") as builtin:
                self.assertTrue(hasattr(builtin, "__call__"))
                self.assertTrue("builtin 'max' at" in str(builtin))


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
