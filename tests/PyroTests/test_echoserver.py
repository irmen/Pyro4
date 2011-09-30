"""
Tests for the built-in test echo server.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import unittest
import time
import Pyro4.test.echoserver as echoserver
import Pyro4
from threading import Thread,Event
from testsupport import *


class EchoServerThread(Thread):
    def __init__(self):
        super(EchoServerThread,self).__init__()
        self.setDaemon(True)
        self.started=Event()
        self.terminated=Event()
    def run(self):
        self.echodaemon,self.echoserver,self.uri=echoserver.main(["-q"], returnWithoutLooping=True)
        self.started.set()
        self.echodaemon.requestLoop(loopCondition=lambda:not self.echoserver.must_shutdown)
        self.terminated.set()
        
class TestEchoserver(unittest.TestCase):
    def setUp(self):
        Pyro4.config.HMAC_KEY=tobytes("testsuite")
        self.echoserverthread=EchoServerThread()
        self.echoserverthread.start()
        self.echoserverthread.started.wait()
        self.uri=self.echoserverthread.uri
    def tearDown(self):
        self.echoserverthread.echodaemon.shutdown()
        time.sleep(0.01)
        self.echoserverthread.terminated.wait()
        Pyro4.config.HMAC_KEY=None
    def testEcho(self):
        echo=Pyro4.Proxy(self.uri)
        try:
            self.assertEqual("hello", echo.echo("hello"))
            self.assertEqual(None, echo.echo(None))
            self.assertEqual([1,2,3], echo.echo([1,2,3]))
        finally:
            echo.shutdown()
    def testError(self):
        try:
            echo=Pyro4.Proxy(self.uri)
            try:
                echo.error()
                self.fail("expected exception")
            except:
                tb="".join(Pyro4.util.getPyroTraceback())
                self.assertTrue("Remote traceback" in tb)
                self.assertTrue("ZeroDivisionError" in tb)
        finally:
            echo.shutdown()


if __name__ == "__main__":
    unittest.main()
