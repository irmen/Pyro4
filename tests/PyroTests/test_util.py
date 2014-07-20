"""
Tests for the utility functions.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import sys
import os
import Pyro4.util
from testsupport import *


# noinspection PyUnusedLocal
def crash(arg=100):
    pre1 = "black"
    pre2 = 999

    # noinspection PyUnusedLocal
    def nest(p1, p2):
        q = "white" + pre1
        x = pre2
        y = arg // 2
        p3 = p1 // p2
        return p3

    a = 10
    b = 0
    s = "hello"
    c = nest(a, b)
    return c


class TestUtils(unittest.TestCase):
    def testFormatTracebackNormal(self):
        try:
            crash()
            self.fail("must crash with ZeroDivisionError")
        except ZeroDivisionError:
            tb = "".join(Pyro4.util.formatTraceback(detailed=False))
            self.assertIn("p3 = p1 // p2", tb)
            self.assertIn("ZeroDivisionError", tb)
            self.assertNotIn(" a = 10", tb)
            self.assertNotIn(" s = 'whiteblack'", tb)
            self.assertNotIn(" pre2 = 999", tb)
            self.assertNotIn(" x = 999", tb)

    def testFormatTracebackDetail(self):
        try:
            crash()
            self.fail("must crash with ZeroDivisionError")
        except ZeroDivisionError:
            tb = "".join(Pyro4.util.formatTraceback(detailed=True))
            self.assertIn("p3 = p1 // p2", tb)
            self.assertIn("ZeroDivisionError", tb)
            if sys.platform != "cli":
                self.assertIn(" a = 10", tb)
                self.assertIn(" q = 'whiteblack'", tb)
                self.assertIn(" pre2 = 999", tb)
                self.assertIn(" x = 999", tb)

    def testPyroTraceback(self):
        try:
            crash()
            self.fail("must crash with ZeroDivisionError")
        except ZeroDivisionError:
            pyro_tb = Pyro4.util.formatTraceback(detailed=True)
            if sys.platform != "cli":
                self.assertIn(" Extended stacktrace follows (most recent call last)\n", pyro_tb)
        try:
            crash("stringvalue")
            self.fail("must crash with TypeError")
        except TypeError:
            x = sys.exc_info()[1]
            x._pyroTraceback = pyro_tb  # set the remote traceback info
            pyrotb = "".join(Pyro4.util.getPyroTraceback())
            self.assertIn("Remote traceback", pyrotb)
            self.assertIn("crash(\"stringvalue\")", pyrotb)
            self.assertIn("TypeError:", pyrotb)
            self.assertIn("ZeroDivisionError", pyrotb)
            del x._pyroTraceback
            pyrotb = "".join(Pyro4.util.getPyroTraceback())
            self.assertNotIn("Remote traceback", pyrotb)
            self.assertNotIn("ZeroDivisionError", pyrotb)
            self.assertIn("crash(\"stringvalue\")", pyrotb)
            self.assertIn("TypeError:", pyrotb)

    def testPyroTracebackArgs(self):
        try:
            crash()
            self.fail("must crash with ZeroDivisionError")
        except ZeroDivisionError:
            ex_type, ex_value, ex_tb = sys.exc_info()
            x = ex_value
            tb1 = Pyro4.util.getPyroTraceback()
            tb2 = Pyro4.util.getPyroTraceback(ex_type, ex_value, ex_tb)
            self.assertEqual(tb1, tb2)
            tb1 = Pyro4.util.formatTraceback()
            tb2 = Pyro4.util.formatTraceback(ex_type, ex_value, ex_tb)
            self.assertEqual(tb1, tb2)
            tb2 = Pyro4.util.formatTraceback(detailed=True)
            if sys.platform != "cli":
                self.assertNotEqual(tb1, tb2)
            # old call syntax, should get an error now:
            self.assertRaises(TypeError, Pyro4.util.getPyroTraceback, x)
            self.assertRaises(TypeError, Pyro4.util.formatTraceback, x)

    def testExcepthook(self):
        # simply test the excepthook by calling it the way Python would
        try:
            crash()
            self.fail("must crash with ZeroDivisionError")
        except ZeroDivisionError:
            pyro_tb = Pyro4.util.formatTraceback()
        try:
            crash("stringvalue")
            self.fail("must crash with TypeError")
        except TypeError:
            ex_type, ex_value, ex_tb = sys.exc_info()
            ex_value._pyroTraceback = pyro_tb  # set the remote traceback info
            oldstderr = sys.stderr
            try:
                sys.stderr = StringIO()
                Pyro4.util.excepthook(ex_type, ex_value, ex_tb)
                output = sys.stderr.getvalue()
                self.assertIn("Remote traceback", output)
                self.assertIn("crash(\"stringvalue\")", output)
                self.assertIn("TypeError:", output)
                self.assertIn("ZeroDivisionError", output)
            finally:
                sys.stderr = oldstderr

    def clearEnv(self):
        if "PYRO_HOST" in os.environ:
            del os.environ["PYRO_HOST"]
        if "PYRO_NS_PORT" in os.environ:
            del os.environ["PYRO_NS_PORT"]
        if "PYRO_COMPRESSION" in os.environ:
            del os.environ["PYRO_COMPRESSION"]
        Pyro4.config.reset()

    def testConfig(self):
        self.clearEnv()
        try:
            self.assertEqual(9090, Pyro4.config.NS_PORT)
            self.assertEqual("localhost", Pyro4.config.HOST)
            self.assertEqual(False, Pyro4.config.COMPRESSION)
            os.environ["NS_PORT"] = "4444"
            Pyro4.config.reset()
            self.assertEqual(9090, Pyro4.config.NS_PORT)
            os.environ["PYRO_NS_PORT"] = "4444"
            os.environ["PYRO_HOST"] = "something.com"
            os.environ["PYRO_COMPRESSION"] = "OFF"
            Pyro4.config.reset()
            self.assertEqual(4444, Pyro4.config.NS_PORT)
            self.assertEqual("something.com", Pyro4.config.HOST)
            self.assertEqual(False, Pyro4.config.COMPRESSION)
        finally:
            self.clearEnv()
            self.assertEqual(9090, Pyro4.config.NS_PORT)
            self.assertEqual("localhost", Pyro4.config.HOST)
            self.assertEqual(False, Pyro4.config.COMPRESSION)

    def testConfigReset(self):
        try:
            Pyro4.config.reset()
            self.assertEqual("localhost", Pyro4.config.HOST)
            Pyro4.config.HOST = "foobar"
            self.assertEqual("foobar", Pyro4.config.HOST)
            Pyro4.config.reset()
            self.assertEqual("localhost", Pyro4.config.HOST)
            os.environ["PYRO_HOST"] = "foobar"
            Pyro4.config.reset()
            self.assertEqual("foobar", Pyro4.config.HOST)
            del os.environ["PYRO_HOST"]
            Pyro4.config.reset()
            self.assertEqual("localhost", Pyro4.config.HOST)
        finally:
            self.clearEnv()

    def testResolveAttr(self):
        class Test(object):
            def __init__(self, value):
                self.value = value

            def __str__(self):
                return "<%s>" % self.value

            def _p(self):
                return "should not be allowed"

            def __p__(self):
                return "should not be allowed"

        obj = Test("obj")
        obj.a = Test("a")
        obj.a.b = Test("b")
        obj.a.b.c = Test("c")
        obj.a._p = Test("p1")
        obj.a._p.q = Test("q1")
        obj.a.__p = Test("p2")
        obj.a.__p.q = Test("q2")
        # check the method with dotted disabled
        self.assertEqual("<a>", str(Pyro4.util.resolveDottedAttribute(obj, "a", False)))
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "_p", False)  # private
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "__p__", False)  # private
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "a.b", False)
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "a.b.c", False)
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "a.b.c.d", False)
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "a._p", False)
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "a._p.q", False)
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "a.__p.q", False)
        # now with dotted enabled
        self.assertEqual("<a>", str(Pyro4.util.resolveDottedAttribute(obj, "a", True)))
        self.assertEqual("<b>", str(Pyro4.util.resolveDottedAttribute(obj, "a.b", True)))
        self.assertEqual("<c>", str(Pyro4.util.resolveDottedAttribute(obj, "a.b.c", True)))
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "a.b.c.d", True)  # doesn't exist
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "_p", True)  # private
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "__p__", True)  # private
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "a._p", True)  # private
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "a._p.q", True)  # private
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "a.__p.q", True)  # private

    @unittest.skipUnless(sys.version_info >= (2, 6, 5), "unicode kwargs needs 2.6.5 or newer")
    def testUnicodeKwargs(self):
        # test the way the interpreter deals with unicode function kwargs
        # those are supported by Python after 2.6.5
        def function(*args, **kwargs):
            return args, kwargs

        processed_args = function(*(1, 2, 3), **{unichr(65): 42})
        self.assertEqual(((1, 2, 3), {unichr(65): 42}), processed_args)
        processed_args = function(*(1, 2, 3), **{unichr(0x20ac): 42})
        key = list(processed_args[1].keys())[0]
        self.assertTrue(type(key) is unicode)
        self.assertEqual(key, unichr(0x20ac))
        self.assertEqual(((1, 2, 3), {unichr(0x20ac): 42}), processed_args)


class TestMeta(unittest.TestCase):
    def testBasic(self):
        o = MyThing("irmen")
        m1 = Pyro4.util.get_exposed_members(o)
        m2 = Pyro4.util.get_exposed_members(MyThing)
        self.assertEqual(m1, m2)
        keys = m1.keys()
        self.assertEqual(3, len(keys))
        self.assertIn("methods", keys)
        self.assertIn("attrs", keys)
        self.assertIn("oneway", keys)

    def testPrivate(self):
        o = MyThing("irmen")
        m = Pyro4.util.get_exposed_members(o)
        for p in ["_private_attr1", "__private_attr2", "__private__", "__private", "_private", "__init__"]:
            self.assertNotIn(p, m["methods"])
            self.assertNotIn(p, m["attrs"])
            self.assertNotIn(p, m["oneway"])

    def testNotOnlyExposed(self):
        o = MyThing("irmen")
        m = Pyro4.util.get_exposed_members(o, only_exposed=False)
        self.assertEqual(set(["prop1", "prop2", "readonly_prop1"]), m["attrs"])
        self.assertEqual(set(["oneway"]), m["oneway"])
        self.assertEqual(set(["classmethod", "oneway", "method", "staticmethod", "exposed"]), m["methods"])

    def testOnlyExposed(self):
        o = MyThing("irmen")
        m = Pyro4.util.get_exposed_members(o)
        self.assertEqual(set(["prop1", "readonly_prop1"]), m["attrs"])
        self.assertEqual(set(), m["oneway"])
        self.assertEqual(set(["exposed"]), m["methods"])

    def testExposedClass(self):
        o = MyThingExposed("irmen")
        m = Pyro4.util.get_exposed_members(o)
        self.assertEqual(set(["name", "readonly_name"]), m["attrs"])
        self.assertEqual(set(["remotemethod"]), m["oneway"])
        self.assertEqual(set(["classmethod", "foo", "staticmethod", "remotemethod"]), m["methods"])

    def testOnlyExposedSub(self):
        o = MyThingSub("irmen")
        m = Pyro4.util.get_exposed_members(o)
        self.assertEqual(set(["prop1", "readonly_prop1"]), m["attrs"])
        self.assertEqual(set(), m["oneway"])
        self.assertEqual(set(["sub_exposed", "exposed"]), m["methods"])

    def testExposedSubclass(self):
        o = MyThingExposedSub("irmen")
        m = Pyro4.util.get_exposed_members(o)
        self.assertEqual(set(["name", "readonly_name"]), m["attrs"])
        self.assertEqual(set(["remotemethod"]), m["oneway"])
        self.assertEqual(set(["classmethod", "foo", "staticmethod", "remotemethod"]), m["methods"])

    def testExposePrivateFails(self):
        with self.assertRaises(AttributeError):
            class Test1(object):
                @Pyro4.expose
                def _private(self):
                    pass
        with self.assertRaises(AttributeError):
            class Test2(object):
                @Pyro4.expose
                def __private__(self):
                    pass
        with self.assertRaises(AttributeError):
            @Pyro4.expose
            class _Test3(object):
                pass

    def testGetExposedProperty(self):
        o = MyThingExposed("irmen")
        with self.assertRaises(AttributeError):
            Pyro4.util.get_exposed_property_value(o, "blurp")
        with self.assertRaises(AttributeError):
            Pyro4.util.get_exposed_property_value(o, "_name")
        with self.assertRaises(AttributeError):
            Pyro4.util.get_exposed_property_value(o, "unexisting_attribute")
        self.assertEqual("irmen", Pyro4.util.get_exposed_property_value(o, "name"))

    def testGetExposedPropertyFromPartiallyExposed(self):
        o = MyThing("irmen")
        with self.assertRaises(AttributeError):
            Pyro4.util.get_exposed_property_value(o, "propvalue")
        with self.assertRaises(AttributeError):
            Pyro4.util.get_exposed_property_value(o, "_name")
        with self.assertRaises(AttributeError):
            Pyro4.util.get_exposed_property_value(o, "prop2")
        with self.assertRaises(AttributeError):
            Pyro4.util.get_exposed_property_value(o, "unexisting_attribute")
        self.assertEqual(42, Pyro4.util.get_exposed_property_value(o, "prop1"))

    def testSetExposedProperty(self):
        o = MyThingExposed("irmen")
        with self.assertRaises(AttributeError):
            Pyro4.util.set_exposed_property_value(o, "blurp", 99)
        with self.assertRaises(AttributeError):
            Pyro4.util.set_exposed_property_value(o, "_name", "error")
        with self.assertRaises(AttributeError):
            Pyro4.util.set_exposed_property_value(o, "unexisting_attribute", 42)
        with self.assertRaises(AttributeError):
            Pyro4.util.set_exposed_property_value(o, "readonly_name", "new_name")
        Pyro4.util.set_exposed_property_value(o, "name", "new_name")
        self.assertEqual("new_name", o.name)

    def testSetExposedPropertyFromPartiallyExposed(self):
        o = MyThing("irmen")
        with self.assertRaises(AttributeError):
            Pyro4.util.set_exposed_property_value(o, "propvalue", 99)
        with self.assertRaises(AttributeError):
            Pyro4.util.set_exposed_property_value(o, "_name", "error")
        with self.assertRaises(AttributeError):
            Pyro4.util.set_exposed_property_value(o, "prop2", 99)
        with self.assertRaises(AttributeError):
            Pyro4.util.set_exposed_property_value(o, "unexisting_attribute", 42)
        with self.assertRaises(AttributeError):
            Pyro4.util.set_exposed_property_value(o, "readonly_prop1", 42)
        Pyro4.util.set_exposed_property_value(o, "prop1", 998877)
        self.assertEqual(998877, o.propvalue)
        with self.assertRaises(AttributeError):
            Pyro4.util.set_exposed_property_value(o, "prop2", 998877)


if __name__ == "__main__":
    # import sys; sys.argv = ['', 'Test.testName']
    unittest.main()
