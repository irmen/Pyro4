"""
Tests for the low level socket functions.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import socket
import os
import sys
import platform
import time
import unittest
import Pyro4.socketutil as SU
from Pyro4 import threadutil, errors
from Pyro4.socketserver.multiplexserver import SocketServer_Multiplex
from Pyro4.socketserver.threadpoolserver import SocketServer_Threadpool
from Pyro4.core import Daemon
import Pyro4.message
import Pyro4.util
import Pyro4.constants
from testsupport import *


# determine ipv6 capability
has_ipv6 = socket.has_ipv6
if has_ipv6:
    s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    try:
        s.connect(("::1", 53))
        s.close()
        socket.getaddrinfo("localhost", 53, socket.AF_INET6)
    except socket.error:
        has_ipv6 = False


class TestSocketStuff(unittest.TestCase):
    def testSockname(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", 0))
        s.listen(5)
        host, port = s.getsockname()
        self.assertNotEqual(0, port)
        self.assertEqual("0.0.0.0", host)  # ipv4 support only at this time
        s.close()


class TestSocketutil(unittest.TestCase):
    def setUp(self):
        Pyro4.config.POLLTIMEOUT = 0.1

    def testGetIP(self):
        Pyro4.config.PREFER_IP_VERSION = 4
        myip = SU.getIpAddress("")
        self.assertTrue(len(myip) > 4)
        myip = SU.getIpAddress("", workaround127=True)
        self.assertTrue(len(myip) > 4)
        self.assertFalse(myip.startswith("127."))
        self.assertEqual("127.0.0.1", SU.getIpAddress("127.0.0.1", workaround127=False))
        self.assertNotEqual("127.0.0.1", SU.getIpAddress("127.0.0.1", workaround127=True))

    @unittest.skipUnless(has_ipv6, "ipv6 testcase")
    def testGetIP6(self):
        self.assertIn(":", SU.getIpAddress("::1", ipVersion=6))
        # self.assertTrue(":" in SU.getIpAddress("", ipVersion=6))
        self.assertIn(":", SU.getIpAddress("localhost", ipVersion=6))

    def testGetIpVersion4(self):
        version = Pyro4.config.PREFER_IP_VERSION
        try:
            Pyro4.config.PREFER_IP_VERSION = 4
            self.assertEqual(4, SU.getIpVersion("127.0.0.1"))
            self.assertEqual(4, SU.getIpVersion("localhost"))
            Pyro4.config.PREFER_IP_VERSION = 0
            self.assertEqual(4, SU.getIpVersion("127.0.0.1"))
        finally:
            Pyro4.config.PREFER_IP_VERSION = version

    @unittest.skipUnless(has_ipv6, "ipv6 testcase")
    def testGetIpVersion6(self):
        version = Pyro4.config.PREFER_IP_VERSION
        try:
            Pyro4.config.PREFER_IP_VERSION = 6
            self.assertEqual(6, SU.getIpVersion("::1"))
            self.assertEqual(6, SU.getIpVersion("localhost"))
            Pyro4.config.PREFER_IP_VERSION = 4
            self.assertEqual(4, SU.getIpVersion("127.0.0.1"))
            self.assertEqual(6, SU.getIpVersion("::1"))
            Pyro4.config.PREFER_IP_VERSION = 0
            self.assertEqual(4, SU.getIpVersion("127.0.0.1"))
            self.assertEqual(6, SU.getIpVersion("::1"))
        finally:
            Pyro4.config.PREFER_IP_VERSION = version

    def testGetInterfaceAddress(self):
        self.assertTrue(SU.getInterfaceAddress("localhost").startswith("127."))
        if has_ipv6:
            self.assertIn(":", SU.getInterfaceAddress("::1"))

    def testUnusedPort(self):
        port1 = SU.findProbablyUnusedPort()
        port2 = SU.findProbablyUnusedPort()
        self.assertTrue(port1 > 0)
        self.assertNotEqual(port1, port2)
        port1 = SU.findProbablyUnusedPort(socktype=socket.SOCK_DGRAM)
        port2 = SU.findProbablyUnusedPort(socktype=socket.SOCK_DGRAM)
        self.assertTrue(port1 > 0)
        self.assertNotEqual(port1, port2)

    @unittest.skipUnless(has_ipv6, "ipv6 testcase")
    def testUnusedPort6(self):
        port1 = SU.findProbablyUnusedPort(family=socket.AF_INET6)
        port2 = SU.findProbablyUnusedPort(family=socket.AF_INET6)
        self.assertTrue(port1 > 0)
        self.assertNotEqual(port1, port2)
        port1 = SU.findProbablyUnusedPort(family=socket.AF_INET6, socktype=socket.SOCK_DGRAM)
        port2 = SU.findProbablyUnusedPort(family=socket.AF_INET6, socktype=socket.SOCK_DGRAM)
        self.assertTrue(port1 > 0)
        self.assertNotEqual(port1, port2)

    def testBindUnusedPort(self):
        sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port1 = SU.bindOnUnusedPort(sock1)
        port2 = SU.bindOnUnusedPort(sock2)
        self.assertTrue(port1 > 0)
        self.assertNotEqual(port1, port2)
        sockname = sock1.getsockname()
        self.assertEqual(("127.0.0.1", port1), sockname)
        sock1.close()
        sock2.close()

    @unittest.skipUnless(has_ipv6, "ipv6 testcase")
    def testBindUnusedPort6(self):
        sock1 = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock2 = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        port1 = SU.bindOnUnusedPort(sock1)
        port2 = SU.bindOnUnusedPort(sock2)
        self.assertTrue(port1 > 0)
        self.assertNotEqual(port1, port2)
        host, port, _, _ = sock1.getsockname()
        self.assertIn(":", host)
        self.assertEqual(port1, port)
        sock1.close()
        sock2.close()

    def testCreateUnboundSockets(self):
        s = SU.createSocket()
        self.assertEqual(socket.AF_INET, s.family)
        bs = SU.createBroadcastSocket()
        self.assertEqual(socket.AF_INET, bs.family)
        try:
            host, port = s.getsockname()
            # can either fail with socket.error or return (host,0)
            self.assertEqual(0, port)
        except socket.error:
            pass
        try:
            host, port = bs.getsockname()
            # can either fail with socket.error or return (host,0)
            self.assertEqual(0, port)
        except socket.error:
            pass
        s.close()
        bs.close()

    @unittest.skipUnless(has_ipv6, "ipv6 testcase")
    def testCreateUnboundSockets6(self):
        s = SU.createSocket(ipv6=True)
        self.assertEqual(socket.AF_INET6, s.family)
        bs = SU.createBroadcastSocket(ipv6=True)
        self.assertEqual(socket.AF_INET6, bs.family)
        try:
            host, port, _, _ = s.getsockname()
            # can either fail with socket.error or return (host,0)
            self.assertEqual(0, port)
        except socket.error:
            pass
        try:
            host, port, _, _ = bs.getsockname()
            # can either fail with socket.error or return (host,0)
            self.assertEqual(0, port)
        except socket.error:
            pass
        s.close()
        bs.close()

    def testCreateBoundSockets(self):
        s = SU.createSocket(bind=('127.0.0.1', 0))
        self.assertEqual(socket.AF_INET, s.family)
        bs = SU.createBroadcastSocket(bind=('127.0.0.1', 0))
        self.assertEqual('127.0.0.1', s.getsockname()[0])
        self.assertEqual('127.0.0.1', bs.getsockname()[0])
        s.close()
        bs.close()
        self.assertRaises(ValueError, SU.createSocket, bind=('localhost', 12345), connect=('localhost', 1234))

    @unittest.skipUnless(has_ipv6, "ipv6 testcase")
    def testCreateBoundSockets6(self):
        s = SU.createSocket(bind=('::1', 0))
        self.assertEqual(socket.AF_INET6, s.family)
        bs = SU.createBroadcastSocket(bind=('::1', 0))
        self.assertIn(':', s.getsockname()[0])
        self.assertIn(':', bs.getsockname()[0])
        s.close()
        bs.close()
        self.assertRaises(ValueError, SU.createSocket, bind=('::1', 12345), connect=('::1', 1234))

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "unix domain sockets required")
    def testCreateBoundUnixSockets(self):
        SOCKNAME = "test_unixsocket"
        if os.path.exists(SOCKNAME):
            os.remove(SOCKNAME)
        s = SU.createSocket(bind=SOCKNAME)
        self.assertEqual(socket.AF_UNIX, s.family)
        self.assertEqual(SOCKNAME, s.getsockname())
        s.close()
        if os.path.exists(SOCKNAME):
            os.remove(SOCKNAME)
        # unicode arg
        SOCKNAME = unicode(SOCKNAME)
        s = SU.createSocket(bind=SOCKNAME)
        self.assertEqual(socket.AF_UNIX, s.family)
        self.assertEqual(SOCKNAME, s.getsockname())
        s.close()
        if os.path.exists(SOCKNAME):
            os.remove(SOCKNAME)
        self.assertRaises(ValueError, SU.createSocket, bind=SOCKNAME, connect=SOCKNAME)

    @unittest.skipUnless(hasattr(socket, "AF_UNIX") and sys.platform.startswith("linux"), "linux and unix domain sockets required")
    def testAbstractNamespace(self):
        SOCKNAME = "\0test_unixsocket_abstract_ns"  # mind the \0 at the start
        s = SU.createSocket(bind=SOCKNAME)
        sn_bytes = tobytes(SOCKNAME)
        self.assertEqual(sn_bytes, s.getsockname())
        s.close()

    def testSend(self):
        ss = SU.createSocket(bind=("localhost", 0))
        port = ss.getsockname()[1]
        cs = SU.createSocket(connect=("localhost", port))
        SU.sendData(cs, tobytes("foobar!") * 10)
        cs.shutdown(socket.SHUT_WR)
        a = ss.accept()
        data = SU.receiveData(a[0], 5)
        self.assertEqual(tobytes("fooba"), data)
        data = SU.receiveData(a[0], 5)
        self.assertEqual(tobytes("r!foo"), data)
        a[0].close()
        ss.close()
        cs.close()

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "unix domain sockets required")
    def testSendUnix(self):
        SOCKNAME = "test_unixsocket"
        ss = SU.createSocket(bind=SOCKNAME)
        cs = SU.createSocket(connect=SOCKNAME)
        SU.sendData(cs, tobytes("foobar!") * 10)
        cs.shutdown(socket.SHUT_WR)
        a = ss.accept()
        data = SU.receiveData(a[0], 5)
        self.assertEqual(tobytes("fooba"), data)
        data = SU.receiveData(a[0], 5)
        self.assertEqual(tobytes("r!foo"), data)
        a[0].close()
        ss.close()
        cs.close()
        if os.path.exists(SOCKNAME):
            os.remove(SOCKNAME)

    def testBroadcast(self):
        ss = SU.createBroadcastSocket((None, 0))
        port = ss.getsockname()[1]
        cs = SU.createBroadcastSocket()
        for bcaddr in Pyro4.config.parseAddressesString(Pyro4.config.BROADCAST_ADDRS):
            try:
                cs.sendto(tobytes("monkey"), 0, (bcaddr, port))
            except socket.error:
                x = sys.exc_info()[1]
                err = getattr(x, "errno", x.args[0])
                # handle some errno that some platforms like to throw
                if err not in Pyro4.socketutil.ERRNO_EADDRNOTAVAIL and err not in Pyro4.socketutil.ERRNO_EADDRINUSE:
                    raise
        data, _ = ss.recvfrom(500)
        self.assertEqual(tobytes("monkey"), data)
        cs.close()
        ss.close()

    def testMsgWaitallProblems(self):
        ss = SU.createSocket(bind=("localhost", 0), timeout=2)
        port = ss.getsockname()[1]
        cs = SU.createSocket(connect=("localhost", port), timeout=2)
        a = ss.accept()
        # test some sizes that might be problematic with MSG_WAITALL and check that they work fine
        for size in [1000, 10000, 32000, 32768, 32780, 41950, 41952, 42000, 65000, 65535, 65600, 80000]:
            SU.sendData(cs, tobytes("x") * size)
            data = SU.receiveData(a[0], size)
            SU.sendData(a[0], data)
            data = SU.receiveData(cs, size)
            self.assertEqual(size, len(data))
        a[0].close()
        ss.close()
        cs.close()

    def testMsgWaitallProblems2(self):
        class ReceiveThread(threadutil.Thread):
            def __init__(self, sock, sizes):
                super(ReceiveThread, self).__init__()
                self.sock = sock
                self.sizes = sizes

            def run(self):
                cs, _ = self.sock.accept()
                for size in self.sizes:
                    data = SU.receiveData(cs, size)
                    SU.sendData(cs, data)
                cs.close()

        ss = SU.createSocket(bind=("localhost", 0))
        SIZES = [1000, 10000, 32000, 32768, 32780, 41950, 41952, 42000, 65000, 65535, 65600, 80000, 999999]
        serverthread = ReceiveThread(ss, SIZES)
        serverthread.setDaemon(True)
        serverthread.start()
        port = ss.getsockname()[1]
        cs = SU.createSocket(connect=("localhost", port), timeout=2)
        # test some sizes that might be problematic with MSG_WAITALL and check that they work fine
        for size in SIZES:
            SU.sendData(cs, tobytes("x") * size)
            data = SU.receiveData(cs, size)
            self.assertEqual(size, len(data))
        serverthread.join()
        ss.close()
        cs.close()

    def testMsgWaitAllConfig(self):
        if platform.system() == "Windows":
            # default config should be False on these platforms even though socket.MSG_WAITALL might exist
            self.assertFalse(Pyro4.config.USE_MSG_WAITALL)
        else:
            # on all other platforms, default config should be True (as long as socket.MSG_WAITALL exists)
            if hasattr(socket, "MSG_WAITALL"):
                self.assertTrue(Pyro4.config.USE_MSG_WAITALL)
            else:
                self.assertFalse(Pyro4.config.USE_MSG_WAITALL)


class ServerCallback(object):
    def _handshake(self, connection):
        raise RuntimeError("this handshake method should never be called")

    def handleRequest(self, connection):
        if not isinstance(connection, SU.SocketConnection):
            raise TypeError("handleRequest expected SocketConnection parameter")
        msg = Pyro4.message.Message.recv(connection, [Pyro4.message.MSG_PING])
        if msg.type == Pyro4.message.MSG_PING:
            msg = Pyro4.message.Message(Pyro4.message.MSG_PING, b"ping", msg.serializer_id, 0, msg.seq)
            connection.send(msg.to_bytes())
        else:
            print("unhandled message type", msg.type)
            connection.close()


class ServerCallback_BrokenHandshake(ServerCallback):
    def _handshake(self, connection):
        raise ZeroDivisionError("handshake crashed (on purpose)")


class TestDaemon(Daemon):
    def __init__(self):
        super(TestDaemon, self).__init__()


class TestSocketServer(unittest.TestCase):
    def testServer_thread(self):
        daemon = ServerCallback()
        port = SU.findProbablyUnusedPort()
        serv = SocketServer_Threadpool()
        serv.init(daemon, "localhost", port)
        self.assertEqual("localhost:" + str(port), serv.locationStr)
        self.assertIsNotNone(serv.sock)
        conn = SU.SocketConnection(serv.sock, "ID12345")
        self.assertEqual("ID12345", conn.objectId)
        self.assertIsNotNone(conn.sock)
        conn.close()
        conn.close()
        self.assertIsNotNone(conn.sock, "connections keep their socket object even if it's closed")
        serv.close()
        serv.close()
        self.assertIsNone(serv.sock)

    def testServer_multiplex(self):
        daemon = ServerCallback()
        port = SU.findProbablyUnusedPort()
        serv = SocketServer_Multiplex()
        serv.init(daemon, "localhost", port)
        self.assertEqual("localhost:" + str(port), serv.locationStr)
        self.assertIsNotNone(serv.sock)
        conn = SU.SocketConnection(serv.sock, "ID12345")
        self.assertEqual("ID12345", conn.objectId)
        self.assertIsNotNone(conn.sock)
        conn.close()
        conn.close()
        self.assertIsNotNone(conn.sock, "connections keep their socket object even if it's closed")
        serv.close()
        serv.close()
        self.assertIsNone(serv.sock)


class TestServerDOS_multiplex(unittest.TestCase):
    def setUp(self):
        self.orig_poll_timeout = Pyro4.config.POLLTIMEOUT
        self.orig_comm_timeout = Pyro4.config.COMMTIMEOUT
        Pyro4.config.POLLTIMEOUT = 0.5
        Pyro4.config.COMMTIMEOUT = 0.5
        self.socket_server = SocketServer_Multiplex

    def tearDown(self):
        Pyro4.config.POLLTIMEOUT = self.orig_poll_timeout
        Pyro4.config.COMMTIMEOUT = self.orig_comm_timeout

    class ServerThread(threadutil.Thread):
        def __init__(self, server, daemon):
            threadutil.Thread.__init__(self)
            self.serv = server()
            self.serv.init(daemon(), "localhost", 0)
            self.locationStr = self.serv.locationStr
            self.stop_loop = threadutil.Event()

        def run(self):
            self.serv.loop(loopCondition=lambda: not self.stop_loop.is_set())
            self.serv.close()

    def testConnectCrash(self):
        serv_thread = TestServerDOS_multiplex.ServerThread(self.socket_server, ServerCallback_BrokenHandshake)
        serv_thread.start()
        time.sleep(0.2)
        self.assertTrue(serv_thread.is_alive(), "server thread failed to start")
        try:
            host, port = serv_thread.locationStr.split(':')
            port = int(port)
            try:
                # first connection attempt (will fail because server daemon _handshake crashes)
                csock = SU.createSocket(connect=(host, port))
                conn = SU.SocketConnection(csock, "uri")
                Pyro4.message.Message.recv(conn, [Pyro4.message.MSG_CONNECTOK])
            except errors.ConnectionClosedError:
                pass
            conn.close()
            try:
                # second connection attempt, should still work (i.e. server should still be running)
                csock = SU.createSocket(connect=(host, port))
                conn = SU.SocketConnection(csock, "uri")
                Pyro4.message.Message.recv(conn, [Pyro4.message.MSG_CONNECTOK])
            except errors.ConnectionClosedError:
                pass
        finally:
            conn.close()
            serv_thread.stop_loop.set()
            serv_thread.join()

    def testInvalidMessageCrash(self):
        serv_thread = TestServerDOS_multiplex.ServerThread(self.socket_server, TestDaemon)
        serv_thread.start()
        time.sleep(0.2)
        self.assertTrue(serv_thread.is_alive(), "server thread failed to start")

        def connect(host, port):
            # connect to the server
            csock = SU.createSocket(connect=(host, port))
            conn = SU.SocketConnection(csock, "uri")
            # send the handshake/connect data
            ser = Pyro4.util.get_serializer_by_id(Pyro4.message.SERIALIZER_MARSHAL)
            data, _ = ser.serializeData({"handshake": "hello", "object": Pyro4.constants.DAEMON_NAME}, False)
            msg = Pyro4.message.Message(Pyro4.message.MSG_CONNECT, data, Pyro4.message.SERIALIZER_MARSHAL, 0, 0)
            conn.send(msg.to_bytes())
            # get the handshake/connect response
            Pyro4.message.Message.recv(conn, [Pyro4.message.MSG_CONNECTOK])
            return conn

        conn = None
        try:
            host, port = serv_thread.locationStr.split(':')
            port = int(port)
            conn = connect(host, port)
            # invoke something, but screw up the message (in this case, mess with the protocol version)
            orig_protocol_version = Pyro4.constants.PROTOCOL_VERSION
            Pyro4.constants.PROTOCOL_VERSION = 9999
            msgbytes = Pyro4.message.Message(Pyro4.message.MSG_PING, b"something", 42, 0, 0).to_bytes()
            Pyro4.constants.PROTOCOL_VERSION = orig_protocol_version
            conn.send(msgbytes)  # this should cause an error in the server because of invalid msg
            try:
                msg = Pyro4.message.Message.recv(conn, [Pyro4.message.MSG_RESULT])
                data = msg.data
                if sys.version_info >= (2, 7):
                    data = msg.data.decode("ascii", errors="ignore")  # convert raw message to string to check some stuff
                self.assertIn("Traceback", data)
                self.assertIn("ProtocolError", data)
                self.assertIn("version", data)
            except errors.ConnectionClosedError:
                # invalid message can cause the connection to be closed, this is fine
                pass
            # invoke something again, this should still work (server must still be running, but our client connection was terminated)
            conn.close()
            conn = connect(host, port)
            msg = Pyro4.message.Message(Pyro4.message.MSG_PING, b"something", 42, 0, 999)  # a valid message this time
            conn.send(msg.to_bytes())
            msg = Pyro4.message.Message.recv(conn, [Pyro4.message.MSG_PING])
            self.assertEqual(Pyro4.message.MSG_PING, msg.type)
            self.assertEqual(999, msg.seq)
            self.assertEqual(b"pong", msg.data)
        finally:
            if conn:
                conn.close()
            serv_thread.stop_loop.set()
            serv_thread.join()


class TestServerDOS_threading(TestServerDOS_multiplex):
    def setUp(self):
        super(TestServerDOS_threading, self).setUp()
        self.socket_server = SocketServer_Threadpool
        self.orig_numthreads = Pyro4.config.THREADPOOL_SIZE
        Pyro4.config.THREADPOOL_SIZE = 1

    def tearDown(self):
        Pyro4.config.THREADPOOL_SIZE = self.orig_numthreads


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
