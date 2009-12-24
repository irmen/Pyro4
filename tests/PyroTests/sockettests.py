import unittest
import socket
import Pyro.socketutil as SU

class TestSocketutil(unittest.TestCase):
    def testGetIP(self):
        localip=SU.getIpAddress()
        localhost=socket.getfqdn(localip)
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
