import unittest
import socket
import Pyro.socketutil as SU
from Pyro.socketserver.selectserver import SocketServer as SocketServer_Select
from Pyro.socketserver.threadpoolserver import SocketServer as SocketServer_Threadpool

class TestSocketutil(unittest.TestCase):
    def testGetIP(self):
        localip=SU.getIpAddress()
        localhost=socket.getfqdn(localip)
        self.assertEqual(localip,SU.getIpAddress(localhost))
    def testUnusedPort(self):
        port1=SU.findUnusedPort()
        port2=SU.findUnusedPort()
        self.assertTrue(port1>0)
        self.assertNotEqual(port1,port2)
    def testBindUnusedPort(self):
        sock1=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock2=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port1=SU.bindOnUnusedPort(sock1)
        port2=SU.bindOnUnusedPort(sock2)
        self.assertTrue(port1>0)
        self.assertNotEqual(port1,port2)
        sockname=sock1.getsockname()
        self.assertEquals(("127.0.0.1",port1), sockname)
        sock1.close()
        sock2.close()
    def testCreateUnboundSockets(self):
        s=SU.createSocket()
        bs=SU.createBroadcastSocket()
        self.assertRaises(socket.error, s.getsockname)
        self.assertRaises(socket.error, bs.getsockname)
        s.close()
        bs.close()
    def testCreateBoundSockets(self):
        s=SU.createSocket(bind=('localhost',0))
        bs=SU.createBroadcastSocket(bind=('localhost',0))
        self.assertEqual('127.0.0.1',s.getsockname()[0])
        self.assertEqual('127.0.0.1',bs.getsockname()[0])
        s.close()
        bs.close()
            
    def testSend(self):
        ss=SU.createSocket(bind=("localhost",0))
        port=ss.getsockname()[1]
        cs=SU.createSocket(connect=("localhost",port))
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
        ss=SU.createBroadcastSocket((None, 0))
        port=ss.getsockname()[1]
        cs=SU.createBroadcastSocket()
        cs.sendto("monkey",('<broadcast>',port))
        data,addr=ss.recvfrom(500)
        self.assertEqual("monkey",data)
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
        port=SU.findUnusedPort()
        serv=SocketServer_Threadpool(callback,"localhost",port)
        self.assertEqual("localhost:"+str(port), serv.locationStr)
        self.assertTrue(serv.sock is not None)
        conn=SU.SocketConnection(serv.sock, "ID12345")
        self.assertEqual("ID12345",conn.objectId)
        self.assertTrue(conn.sock is not None)
        conn.close()
        conn.close()
        self.assertTrue(conn.sock is None)
        serv.close()
        serv.close()
        self.assertTrue(serv.sock is None)
    def testServer_select(self):
        callback=ServerCallback()
        port=SU.findUnusedPort()
        serv=SocketServer_Select(callback,"localhost",port)
        self.assertEqual("localhost:"+str(port), serv.locationStr)
        self.assertTrue(serv.sock is not None)
        conn=SU.SocketConnection(serv.sock, "ID12345")
        self.assertEqual("ID12345",conn.objectId)
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
