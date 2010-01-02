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
        data,c=ser.serialize(before,compress=False)
        after=ser.deserialize(data)
        self.assertEqual(before,after)
        self.assertEqual(bool,type(c))
        data,c=ser.serialize(before,compress=True)
        after=ser.deserialize(data,compressed=c)
        self.assertEqual(before,after)
        self.assertEqual(bool,type(c))

    def testSerializeCompression(self):
        smalldata=["wordwordword","blablabla","orangeorange"]
        largedata=["wordwordword"+str(i) for i in range(30)]
        ser=Pyro.util.Serializer()
        data1,compressed=ser.serialize(smalldata,compress=False)
        self.assertFalse(compressed)
        data2,compressed=ser.serialize(smalldata,compress=True)
        self.assertFalse(compressed, "small messages should not be compressed")
        self.assertEquals(len(data1),len(data2))
        data1,compressed=ser.serialize(largedata,compress=False)
        self.assertFalse(compressed)
        data2,compressed=ser.serialize(largedata,compress=True)
        self.assertTrue(compressed, "large messages should be compressed")
        self.assertTrue(len(data1)>len(data2))


    def testConfig(self):
        import Pyro.config
        import os,socket
        def clearEnv():
            if "PYRO_PORT" in os.environ: del os.environ["PYRO_PORT"]
            if "PYRO_HOST" in os.environ: del os.environ["PYRO_HOST"]
            if "PYRO_COMPRESSION" in os.environ: del os.environ["PYRO_COMPRESSION"]
            reload(Pyro.config)
        clearEnv()
        try:
            self.assertEqual(7766, Pyro.config.PORT)
            self.assertEqual(socket.gethostname(), Pyro.config.HOST)
            self.assertEqual(False, Pyro.config.COMPRESSION)
            os.environ["PORT"]="4444"
            reload(Pyro.config)
            self.assertEqual(7766, Pyro.config.PORT)
            os.environ["PYRO_PORT"]="4444"
            os.environ["PYRO_HOST"]="something.com"
            os.environ["PYRO_COMPRESSION"]="OFF"
            reload(Pyro.config)
            self.assertEqual(4444, Pyro.config.PORT)
            self.assertEqual("something.com", Pyro.config.HOST)
            self.assertEqual(False, Pyro.config.COMPRESSION)
        finally:
            clearEnv()
            self.assertEqual(7766, Pyro.config.PORT)
            self.assertEqual(socket.gethostname(), Pyro.config.HOST)
            self.assertEqual(False, Pyro.config.COMPRESSION)
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()