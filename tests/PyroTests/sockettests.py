import unittest
import socket
import Pyro.socketutil as SU

class TestSocketutil(unittest.TestCase):
    def testHostname(self):
        full=SU.getHostname(True)
        short=SU.getHostname(False)
        self.assertFalse('.' in short)
        self.assertTrue('.' in full)
        self.assertTrue(full.startswith(short))
    def testGetIP(self):
        localip=SU.getIpAddress()
        localhost=SU.getHostname(ip=localip)
        self.assertEqual(localip,SU.getIpAddress(localhost))
    def testSend(self):
        ss=SU.createSocket(bind=('localhost',9999))
        cs=SU.createSocket(connect=('localhost',9999))
        SU.sendData(cs,"foobar!"*10)
        cs.shutdown(socket.SHUT_WR)
        a=ss.accept()
        data=SU.receiveData(a[0], 5)
        self.assertEqual("fooba",data)
        data=SU.receiveData(a[0], 5)
        self.assertEqual("r!foo",data)
        a[0].close()
        ss.close()
        cs.close()
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
