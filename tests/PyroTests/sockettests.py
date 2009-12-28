import unittest
import socket
import Pyro.socketutil as SU

class TestSocketutil(unittest.TestCase):
    def testGetIP(self):
        localip=SU.getIpAddress()
        localhost=socket.getfqdn(localip)
        self.assertEqual(localip,SU.getIpAddress(localhost))
    def testSend(self):
        ss=SU.createSocket(bind=("localhost",9999))
        cs=SU.createSocket(connect=("localhost",9999))
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


class ServerCallback(object):
    def handshake(self, connection):
        if not isinstance(connection, SU.SocketConnection):
            raise TypeError("handshake expected SocketConnection parameter")
    def handleRequest(self, connection):
        if not isinstance(connection, SU.SocketConnection):
            raise TypeError("handleRequest expected SocketConnection parameter")

class TestSocketServer(unittest.TestCase):
    def testServer(self):
        callback=ServerCallback()
        serv=SU.SocketServer(callback,"localhost",15555)
        self.assertEqual("localhost:15555", serv.locationStr)
        self.assertTrue(serv.sock is not None)
        self.assertEqual(serv.callback, callback)
        conn=SU.SocketConnection(serv.sock, "12345")
        self.assertEqual("12345",conn.objectId)
        self.assertTrue(conn.sock is not None)
        conn.close()
        conn.close()
        self.assertTrue(conn.sock is None)
        serv.close()
        serv.close()
        self.assertTrue(serv.sock is None)
        self.assertTrue(serv.callback is None)
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
