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
    def testBroadcast(self):
        ss=SU.createBroadcastSocket((None, 8888))
        cs=SU.createBroadcastSocket()
        cs.sendto("monkey",('<broadcast>',8888))
        data,addr=ss.recvfrom(500)
        self.assertEquals("monkey",data)
        cs.close()
        ss.close()

class ServerCallback(object):
    def handshake(self, connection):
        if not isinstance(connection, SU.SocketConnection):
            raise TypeError("handshake expected SocketConnection parameter")
    def handleRequest(self, connection):
        if not isinstance(connection, SU.SocketConnection):
            raise TypeError("handleRequest expected SocketConnection parameter")

class TestSocketServer(unittest.TestCase):
    def testServer_thread(self):
        callback=ServerCallback()
        serv=SU.SocketServer_Threadpool(callback,"localhost",15555)
        self.assertEqual("localhost:15555", serv.locationStr)
        self.assertTrue(serv.sock is not None)
        conn=SU.SocketConnection(serv.sock, "12345")
        self.assertEqual("12345",conn.objectId)
        self.assertTrue(conn.sock is not None)
        conn.close()
        conn.close()
        self.assertTrue(conn.sock is None)
        serv.close()
        serv.close()
        self.assertTrue(serv.sock is None)
    def testServer_select(self):
        callback=ServerCallback()
        serv=SU.SocketServer_Select(callback,"localhost",15555)
        self.assertEqual("localhost:15555", serv.locationStr)
        self.assertTrue(serv.sock is not None)
        conn=SU.SocketConnection(serv.sock, "12345")
        self.assertEqual("12345",conn.objectId)
        self.assertTrue(conn.sock is not None)
        conn.close()
        conn.close()
        self.assertTrue(conn.sock is None)
        serv.close()
        serv.close()
        self.assertTrue(serv.sock is None)
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
