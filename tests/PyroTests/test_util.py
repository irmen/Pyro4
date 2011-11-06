"""
Tests for the utility functions.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import unittest

import sys, imp, os, platform
import Pyro4.util
from testsupport import *

if not hasattr(imp,"reload"):
    imp.reload=reload   # python 2.5 doesn't have imp.reload

def crash(arg=100):
    pre1="black"
    pre2=999
    def nest(p1,p2):
        s="white"+pre1
        x=pre2
        y=arg//2
        p3=p1//p2
        return p3
    a=10
    b=0
    s="hello"
    c=nest(a,b)
    return c

class TestUtils(unittest.TestCase):

    def testFormatTracebackNormal(self):
        try:
            crash()
            self.fail("must crash with ZeroDivisionError")
        except ZeroDivisionError:
            tb="".join(Pyro4.util.formatTraceback(detailed=False))
            self.assertTrue("p3=p1//p2" in tb)
            self.assertTrue("ZeroDivisionError" in tb)
            self.assertFalse(" a = 10" in tb)
            self.assertFalse(" s = 'whiteblack'" in tb)
            self.assertFalse(" pre2 = 999" in tb)
            self.assertFalse(" x = 999" in tb)

    def testFormatTracebackDetail(self):
        try:
            crash()
            self.fail("must crash with ZeroDivisionError")
        except ZeroDivisionError:
            tb="".join(Pyro4.util.formatTraceback(detailed=True))
            self.assertTrue("p3=p1//p2" in tb)
            self.assertTrue("ZeroDivisionError" in tb)
            if sys.platform!="cli":
                self.assertTrue(" a = 10" in tb)
                self.assertTrue(" s = 'whiteblack'" in tb)
                self.assertTrue(" pre2 = 999" in tb)
                self.assertTrue(" x = 999" in tb)


    def testPyroTraceback(self):
        try:
            crash()
            self.fail("must crash with ZeroDivisionError")
        except ZeroDivisionError:
            pyro_tb=Pyro4.util.formatTraceback(detailed=True)
            if sys.platform!="cli":
                self.assertTrue(" Extended stacktrace follows (most recent call last)\n" in pyro_tb)
        try:
            crash("stringvalue")
            self.fail("must crash with TypeError")
        except TypeError:
            x=sys.exc_info()[1]
            x._pyroTraceback=pyro_tb        # set the remote traceback info
            pyrotb="".join(Pyro4.util.getPyroTraceback())
            self.assertTrue("Remote traceback" in pyrotb)
            self.assertTrue("crash(\"stringvalue\")" in pyrotb)
            self.assertTrue("TypeError:" in pyrotb)
            self.assertTrue("ZeroDivisionError" in pyrotb)
            del x._pyroTraceback
            pyrotb="".join(Pyro4.util.getPyroTraceback())
            self.assertFalse("Remote traceback" in pyrotb)
            self.assertFalse("ZeroDivisionError" in pyrotb)
            self.assertTrue("crash(\"stringvalue\")" in pyrotb)
            self.assertTrue("TypeError:" in pyrotb)
            
    def testPyroTracebackArgs(self):
        try:
            crash()
            self.fail("must crash with ZeroDivisionError")
        except ZeroDivisionError:
            ex_type, ex_value, ex_tb = sys.exc_info()
            x=ex_value
            tb1=Pyro4.util.getPyroTraceback()
            tb2=Pyro4.util.getPyroTraceback(ex_type, ex_value, ex_tb)
            self.assertEqual(tb1, tb2)
            tb1=Pyro4.util.formatTraceback()
            tb2=Pyro4.util.formatTraceback(ex_type, ex_value, ex_tb)
            self.assertEqual(tb1, tb2)
            tb2=Pyro4.util.formatTraceback(detailed=True)
            if sys.platform!="cli":
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
            pyro_tb=Pyro4.util.formatTraceback()
        try:
            crash("stringvalue")
            self.fail("must crash with TypeError")
        except TypeError:
            ex_type,ex_value,ex_tb=sys.exc_info()
            ex_value._pyroTraceback=pyro_tb        # set the remote traceback info
            oldstderr=sys.stderr
            try:
                sys.stderr=StringIO()
                Pyro4.util.excepthook(ex_type, ex_value, ex_tb)
                output=sys.stderr.getvalue()
                self.assertTrue("Remote traceback" in output)
                self.assertTrue("crash(\"stringvalue\")" in output)
                self.assertTrue("TypeError:" in output)
                self.assertTrue("ZeroDivisionError" in output)
            finally:
                sys.stderr=oldstderr

    def clearEnv(self):
        if "PYRO_HOST" in os.environ: del os.environ["PYRO_HOST"]
        if "PYRO_NS_PORT" in os.environ: del os.environ["PYRO_NS_PORT"]
        if "PYRO_COMPRESSION" in os.environ: del os.environ["PYRO_COMPRESSION"]
        Pyro4.config.reset(useenvironment=False)
    
    def testConfig(self):
        self.clearEnv()
        try:
            self.assertEqual(9090, Pyro4.config.NS_PORT)
            self.assertEqual("localhost", Pyro4.config.HOST)
            self.assertEqual(False, Pyro4.config.COMPRESSION)
            os.environ["NS_PORT"]="4444"
            Pyro4.config.reset()
            self.assertEqual(9090, Pyro4.config.NS_PORT)
            os.environ["PYRO_NS_PORT"]="4444"
            os.environ["PYRO_HOST"]="something.com"
            os.environ["PYRO_COMPRESSION"]="OFF"
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
            Pyro4.config.reset(useenvironment=False)
            self.assertEqual("localhost", Pyro4.config.HOST)
            Pyro4.config.HOST="foobar"
            self.assertEqual("foobar", Pyro4.config.HOST)
            Pyro4.config.reset(useenvironment=False)
            self.assertEqual("localhost", Pyro4.config.HOST)
            os.environ["PYRO_HOST"]="foobar"
            Pyro4.config.reset(useenvironment=True)
            self.assertEqual("foobar", Pyro4.config.HOST)
            Pyro4.config.reset(useenvironment=False)
            self.assertEqual("localhost", Pyro4.config.HOST)
        finally:
            self.clearEnv()


    def testResolveAttr(self):
        class Test(object):
            def __init__(self,value):
                self.value=value
            def __str__(self):
                return "<%s>" % self.value
        obj=Test("obj")
        obj.a=Test("a")
        obj.a.b=Test("b")
        obj.a.b.c=Test("c")
        obj.a._p=Test("p1")
        obj.a._p.q=Test("q1")
        obj.a.__p=Test("p2")
        obj.a.__p.q=Test("q2")
        #check the method with dotted disabled 
        self.assertEqual("<a>",str(Pyro4.util.resolveDottedAttribute(obj,"a",False)))
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "a.b",False)
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "a.b.c",False)
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "a.b.c.d",False)
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "a._p",False)
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "a._p.q",False)
        self.assertRaises(AttributeError, Pyro4.util.resolveDottedAttribute, obj, "a.__p.q",False)
        #now with dotted enabled
        self.assertEqual("<a>",str(Pyro4.util.resolveDottedAttribute(obj,"a",True)))
        self.assertEqual("<b>",str(Pyro4.util.resolveDottedAttribute(obj,"a.b",True)))
        self.assertEqual("<c>",str(Pyro4.util.resolveDottedAttribute(obj,"a.b.c",True)))
        self.assertRaises(AttributeError,Pyro4.util.resolveDottedAttribute, obj,"a.b.c.d",True)   # doesn't exist
        self.assertRaises(AttributeError,Pyro4.util.resolveDottedAttribute, obj,"a._p",True)    #private
        self.assertRaises(AttributeError,Pyro4.util.resolveDottedAttribute, obj,"a._p.q",True)    #private
        self.assertRaises(AttributeError,Pyro4.util.resolveDottedAttribute, obj,"a.__p.q",True)    #private

    def testUnicodeKwargs(self):
        # test the way the interpreter deals with unicode function kwargs
        # those are supported by Python after 2.6.5, but not (all) by PyPy
        # see https://bugs.pypy.org/issue751
        def function(*args, **kwargs):
            return args, kwargs
        if sys.version_info>=(2,6,5):
            processed_args=function(*(1,2,3), **{ unichr(65): 42 })
            self.assertEqual( ((1,2,3), { unichr(65): 42}), processed_args)
            if platform.python_implementation()!="PyPy":
                processed_args=function(*(1,2,3), **{ unichr(0x20ac): 42 })
                self.assertEqual( ((1,2,3), { unichr(0x20ac): 42}), processed_args)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
