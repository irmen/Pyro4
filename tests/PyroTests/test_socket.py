"""
Tests for the low level socket functions.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import socket, os, sys
import Pyro4.socketutil as SU
from Pyro4 import threadutil
from Pyro4.socketserver.multiplexserver import SocketServer_Select, SocketServer_Poll
from Pyro4.socketserver.threadpoolserver import SocketServer_Threadpool
import Pyro4
from testsupport import *


# determine ipv6 capability
has_ipv6 = socket.has_ipv6
if has_ipv6:
    s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    try:
        s.connect(("::1", 53))
        s.close()
        socket.getaddrinfo("localhost",None,socket.AF_INET6)
    except socket.error:
        has_ipv6 = False


class TestSocketStuff(unittest.TestCase):
    def testSockname(self):
        s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("",0))
        s.listen(5)
        host, port = s.getsockname()
        self.assertNotEqual(0, port)
        self.assertEqual("0.0.0.0", host)     # ipv4 support only at this time
        s.close()


class TestSocketutil(unittest.TestCase):
    def setUp(self):
        Pyro4.config.POLLTIMEOUT=0.1
        
    def testGetIP(self):
        Pyro4.config.PREFER_IP_VERSION=4
        myip=SU.getIpAddress("")
        self.assertTrue(len(myip)>4)
        myip=SU.getIpAddress("",workaround127=True)
        self.assertTrue(len(myip)>4)
        self.assertFalse(myip.startswith("127."))
        self.assertEqual("127.0.0.1", SU.getIpAddress("127.0.0.1",workaround127=False))
        self.assertNotEqual("127.0.0.1", SU.getIpAddress("127.0.0.1",workaround127=True))
        
    def testGetIP6(self):
        if not has_ipv6:
            return
        self.assertTrue(":" in SU.getIpAddress("::1",ipVersion=6))
        self.assertTrue(":" in SU.getIpAddress("",ipVersion=6))
        self.assertTrue(":" in SU.getIpAddress("localhost",ipVersion=6))

    def testGetIpVersion(self):
        if has_ipv6:
            Pyro4.config.PREFER_IP_VERSION=6
            self.assertEqual(6, SU.getIpVersion("127.0.0.1"))
            self.assertEqual(6, SU.getIpVersion("::1"))
            self.assertEqual(6, SU.getIpVersion("localhost"))
        Pyro4.config.PREFER_IP_VERSION=4
        self.assertEqual(4, SU.getIpVersion("127.0.0.1"))
        self.assertEqual(6, SU.getIpVersion("::1"))
        self.assertEqual(4, SU.getIpVersion("localhost"))
        Pyro4.config.PREFER_IP_VERSION=0
        self.assertEqual(4, SU.getIpVersion("127.0.0.1"))
        self.assertEqual(6, SU.getIpVersion("::1"))

    def testGetInterfaceAddress(self):
        self.assertTrue(SU.getInterfaceAddress("localhost").startswith("127."))
        if has_ipv6:
            self.assertTrue(":" in SU.getInterfaceAddress("::1"))

    def testUnusedPort(self):
        port1=SU.findProbablyUnusedPort()
        port2=SU.findProbablyUnusedPort()
        self.assertTrue(port1>0)
        self.assertNotEqual(port1,port2)
        port1=SU.findProbablyUnusedPort(socktype=socket.SOCK_DGRAM)
        port2=SU.findProbablyUnusedPort(socktype=socket.SOCK_DGRAM)
        self.assertTrue(port1>0)
        self.assertNotEqual(port1,port2)

    def testUnusedPort6(self):
        if not has_ipv6:
            return
        port1=SU.findProbablyUnusedPort(family=socket.AF_INET6)
        port2=SU.findProbablyUnusedPort(family=socket.AF_INET6)
        self.assertTrue(port1>0)
        self.assertNotEqual(port1,port2)
        port1=SU.findProbablyUnusedPort(family=socket.AF_INET6, socktype=socket.SOCK_DGRAM)
        port2=SU.findProbablyUnusedPort(family=socket.AF_INET6, socktype=socket.SOCK_DGRAM)
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
        self.assertEqual(("127.0.0.1",port1), sockname)
        sock1.close()
        sock2.close()

    def testBindUnusedPort6(self):
        if not has_ipv6:
            return
        if os.name=="java":
            print("Jython/java ipv6 support isn't quite there yet")
            return
        sock1=socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock2=socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        port1=SU.bindOnUnusedPort(sock1)
        port2=SU.bindOnUnusedPort(sock2)
        self.assertTrue(port1>0)
        self.assertNotEqual(port1,port2)
        host,port,_,_=sock1.getsockname()
        self.assertTrue(":" in host)
        self.assertEqual(port1, port)
        sock1.close()
        sock2.close()

    def testCreateUnboundSockets(self):
        s=SU.createSocket()
        self.assertEqual(socket.AF_INET, s.family)
        bs=SU.createBroadcastSocket()
        self.assertEqual(socket.AF_INET, bs.family)
        try:
            host,port=s.getsockname()
            # can either fail with socket.error or return (host,0)
            self.assertEqual(0,port)
        except socket.error:
            pass
        try:
            host,port=bs.getsockname()
            # can either fail with socket.error or return (host,0)
            self.assertEqual(0,port)
        except socket.error:
            pass
        s.close()
        bs.close()

    def testCreateUnboundSockets6(self):
        if not has_ipv6:
            return
        s=SU.createSocket(ipv6=True)
        self.assertEqual(socket.AF_INET6, s.family)
        bs=SU.createBroadcastSocket(ipv6=True)
        self.assertEqual(socket.AF_INET6, bs.family)
        try:
            host,port,_,_=s.getsockname()
            # can either fail with socket.error or return (host,0)
            self.assertEqual(0,port)
        except socket.error:
            pass
        try:
            host,port,_,_=bs.getsockname()
            # can either fail with socket.error or return (host,0)
            self.assertEqual(0,port)
        except socket.error:
            pass
        s.close()
        bs.close()

    def testCreateBoundSockets(self):
        s=SU.createSocket(bind=('127.0.0.1',0))
        self.assertEqual(socket.AF_INET, s.family)
        bs=SU.createBroadcastSocket(bind=('127.0.0.1',0))
        self.assertEqual('127.0.0.1',s.getsockname()[0])
        self.assertEqual('127.0.0.1',bs.getsockname()[0])
        s.close()
        bs.close()
        self.assertRaises(ValueError, SU.createSocket, bind=('localhost',12345), connect=('localhost',1234))
            
    def testCreateBoundSockets6(self):
        if not has_ipv6:
            return
        s=SU.createSocket(bind=('::1',0))
        self.assertEqual(socket.AF_INET6, s.family)
        bs=SU.createBroadcastSocket(bind=('::1',0))
        self.assertTrue(':' in s.getsockname()[0])
        self.assertTrue(':' in bs.getsockname()[0])
        s.close()
        bs.close()
        self.assertRaises(ValueError, SU.createSocket, bind=('::1',12345), connect=('::1',1234))

    def testCreateBoundUnixSockets(self):
        if hasattr(socket,"AF_UNIX"):
            SOCKNAME="test_unixsocket"
            if os.path.exists(SOCKNAME): os.remove(SOCKNAME)
            s=SU.createSocket(bind=SOCKNAME)
            self.assertEqual(socket.AF_UNIX, s.family)
            self.assertEqual(SOCKNAME,s.getsockname())
            s.close()
            if os.path.exists(SOCKNAME): os.remove(SOCKNAME)
            self.assertRaises(ValueError, SU.createSocket, bind=SOCKNAME, connect=SOCKNAME)

    def testSend(self):
        ss=SU.createSocket(bind=("localhost",0))
        port=ss.getsockname()[1]
        cs=SU.createSocket(connect=("localhost",port))
        SU.sendData(cs,tobytes("foobar!"*10))
        cs.shutdown(socket.SHUT_WR)
        a=ss.accept()
        data=SU.receiveData(a[0], 5)
        self.assertEqual(tobytes("fooba"),data)
        data=SU.receiveData(a[0], 5)
        self.assertEqual(tobytes("r!foo"),data)
        a[0].close()
        ss.close()
        cs.close()

    def testSendUnix(self):
        if hasattr(socket,"AF_UNIX"):
            SOCKNAME="test_unixsocket"
            ss=SU.createSocket(bind=SOCKNAME)
            cs=SU.createSocket(connect=SOCKNAME)
            SU.sendData(cs,tobytes("foobar!"*10))
            cs.shutdown(socket.SHUT_WR)
            a=ss.accept()
            data=SU.receiveData(a[0], 5)
            self.assertEqual(tobytes("fooba"),data)
            data=SU.receiveData(a[0], 5)
            self.assertEqual(tobytes("r!foo"),data)
            a[0].close()
            ss.close()
            cs.close()
            if os.path.exists(SOCKNAME): os.remove(SOCKNAME)

    def testBroadcast(self):
        ss=SU.createBroadcastSocket((None, 0))
        port=ss.getsockname()[1]
        cs=SU.createBroadcastSocket()
        for bcaddr in Pyro4.config.parseAddressesString(Pyro4.config.BROADCAST_ADDRS):
            try:
                cs.sendto(tobytes("monkey"),0,(bcaddr,port))
            except socket.error:
                x=sys.exc_info()[1]
                err=getattr(x, "errno", x.args[0])
                if err not in Pyro4.socketutil.ERRNO_EADDRNOTAVAIL:    # yeah, windows likes to throw these...
                    if err not in Pyro4.socketutil.ERRNO_EADDRINUSE:     # and jython likes to throw thses...
                        raise
        data,_=ss.recvfrom(500)
        self.assertEqual(tobytes("monkey"),data)
        cs.close()
        ss.close()
        
    def testMsgWaitallProblems(self):
        ss=SU.createSocket(bind=("localhost",0), timeout=0.5)
        port=ss.getsockname()[1]
        cs=SU.createSocket(connect=("localhost",port), timeout=0.5)
        a=ss.accept()
        # test some sizes that might be problematic with MSG_WAITALL
        for size in [1000,10000,32000,32768,32780,41950,41952,42000,65000,65535,65600,80000]:
            SU.sendData(cs,tobytes("x")*size)
            data=SU.receiveData(a[0],size)
            SU.sendData(a[0], data)
            data=SU.receiveData(cs,size)
            self.assertEqual(size, len(data))
        a[0].close()
        ss.close()
        cs.close()
        
    def testMsgWaitallProblems2(self):
        class ReceiveThread(threadutil.Thread):
            def __init__(self, sock, sizes):
                super(ReceiveThread,self).__init__()
                self.sock=sock
                self.sizes=sizes
            def run(self):
                cs,_ = self.sock.accept()
                for size in self.sizes:
                    data=SU.receiveData(cs,size)
                    SU.sendData(cs, data)
                cs.close()
        ss=SU.createSocket(bind=("localhost",0))
        SIZES=[1000,10000,32000,32768,32780,41950,41952,42000,65000,65535,65600,80000,999999]
        serverthread=ReceiveThread(ss, SIZES)
        serverthread.setDaemon(True)
        serverthread.start()
        port=ss.getsockname()[1]
        cs=SU.createSocket(connect=("localhost",port), timeout=0.5)
        # test some sizes that might be problematic with MSG_WAITALL
        for size in SIZES:
            SU.sendData(cs,tobytes("x")*size)
            data=SU.receiveData(cs,size)
            self.assertEqual(size, len(data))
        serverthread.join()
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
    def testServer_thread(self):
        daemon=ServerCallback()
        port=SU.findProbablyUnusedPort()
        serv=SocketServer_Threadpool()
        serv.init(daemon,"localhost",port)
        self.assertEqual("localhost:"+str(port), serv.locationStr)
        self.assertTrue(serv.sock is not None)
        conn=SU.SocketConnection(serv.sock, "ID12345")
        self.assertEqual("ID12345",conn.objectId)
        self.assertTrue(conn.sock is not None)
        conn.close()
        conn.close()
        self.assertFalse(conn.sock is None, "connections keep their socket object even if it's closed")
        serv.close()
        serv.close()
        self.assertTrue(serv.sock is None)
    def testServer_select(self):
        daemon=ServerCallback()
        port=SU.findProbablyUnusedPort()
        serv=SocketServer_Select()
        serv.init(daemon,"localhost",port)
        self.assertEqual("localhost:"+str(port), serv.locationStr)
        self.assertTrue(serv.sock is not None)
        conn=SU.SocketConnection(serv.sock, "ID12345")
        self.assertEqual("ID12345",conn.objectId)
        self.assertTrue(conn.sock is not None)
        conn.close()
        conn.close()
        self.assertFalse(conn.sock is None, "connections keep their socket object even if it's closed")
        serv.close()
        serv.close()
        self.assertTrue(serv.sock is None)
    def testServer_poll(self):
        daemon=ServerCallback()
        port=SU.findProbablyUnusedPort()
        serv=SocketServer_Poll()
        serv.init(daemon,"localhost",port)
        self.assertEqual("localhost:"+str(port), serv.locationStr)
        self.assertTrue(serv.sock is not None)
        conn=SU.SocketConnection(serv.sock, "ID12345")
        self.assertEqual("ID12345",conn.objectId)
        self.assertTrue(conn.sock is not None)
        conn.close()
        conn.close()
        self.assertFalse(conn.sock is None, "connections keep their socket object even if it's closed")
        serv.close()
        serv.close()
        self.assertTrue(serv.sock is None)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
