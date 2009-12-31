import unittest

import sys
import Pyro.util

def crash(arg=100):
    pre1="black"
    pre2=999
    def nest(p1,p2):
        s="white"+pre1 #@UnusedVariable
        x=pre2 #@UnusedVariable
        y=arg/2 #@UnusedVariable
        p3=p1/p2
        return p3
    a=10
    b=0
    s="hello" #@UnusedVariable
    c=nest(a,b)
    return c

class TestUtils(unittest.TestCase):

    def testFormatTracebackNormal(self):
        try:
            crash()
        except:
            tb="".join(Pyro.util.formatTraceback(detailed=False))
            self.assertTrue("p3=p1/p2" in tb)
            self.assertTrue("ZeroDivisionError" in tb)
            self.assertFalse(" a = 10" in tb)
            self.assertFalse(" s = 'whiteblack'" in tb)
            self.assertFalse(" pre2 = 999" in tb)
            self.assertFalse(" x = 999" in tb)

    def testFormatTracebackDetail(self):
        try:
            crash()
        except:
            tb="".join(Pyro.util.formatTraceback(detailed=True))
            self.assertTrue("p3=p1/p2" in tb)
            self.assertTrue("ZeroDivisionError" in tb)
            if " a = 10" not in tb:
                self.failIfEqual("cli",sys.platform,"detailed tracebacks don't work in IronPython (ignore this fail)")
            self.assertTrue(" a = 10" in tb)
            self.assertTrue(" s = 'whiteblack'" in tb)
            self.assertTrue(" pre2 = 999" in tb)
            self.assertTrue(" x = 999" in tb)


    def testPyroTraceback(self):
        try:
            crash()
        except:
            pyro_tb=Pyro.util.formatTraceback(detailed=True)
        try:
            crash("stringvalue")
        except Exception,x: 
            setattr(x, Pyro.constants.TRACEBACK_ATTRIBUTE, pyro_tb)
            pyrotb="".join(Pyro.util.getPyroTraceback())
            self.assertTrue("crash(\"stringvalue\")" in pyrotb)
            self.assertTrue("TypeError:" in pyrotb)
            self.assertTrue("Remote traceback" in pyrotb)
            self.assertTrue("ZeroDivisionError" in pyrotb)

    def testSerialize(self):
        ser=Pyro.util.Serializer()
        before=(42, ["a","b","c"], {"henry": 998877, "suzie": 776655})
        pickle=ser.serialize(before)
        after=ser.deserialize(pickle)
        self.assertEqual(before,after)
        
    def testConfig(self):
        import Pyro.config
        import os
        try:
            self.assertEqual(7766, Pyro.config.PORT)
            self.assertEqual("localhost", Pyro.config.SERVERHOST)
            self.assertEqual(False, Pyro.config.COMPRESSION)
            os.environ["PORT"]="4444"
            reload(Pyro.config)
            self.assertEqual(7766, Pyro.config.PORT)
            os.environ["PYRO_PORT"]="4444"
            os.environ["PYRO_SERVERHOST"]="something.com"
            os.environ["PYRO_COMPRESSION"]="OFF"
            reload(Pyro.config)
            self.assertEqual(4444, Pyro.config.PORT)
            self.assertEqual("something.com", Pyro.config.SERVERHOST)
            self.assertEqual(False, Pyro.config.COMPRESSION)
        finally:
            del os.environ["PYRO_PORT"]
            del os.environ["PYRO_SERVERHOST"]
            del os.environ["PYRO_COMPRESSION"]
            reload(Pyro.config)
            self.assertEqual(7766, Pyro.config.PORT)
            self.assertEqual("localhost", Pyro.config.SERVERHOST)
            self.assertEqual(False, Pyro.config.COMPRESSION)
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()