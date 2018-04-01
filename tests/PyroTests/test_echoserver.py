"""
Tests for the built-in test echo server.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import time
import unittest
from threading import Thread, Event
import Pyro4.test.echoserver as echoserver
import Pyro4.util
from Pyro4.configuration import config


class EchoServerThread(Thread):
    def __init__(self):
        super(EchoServerThread, self).__init__()
        self.setDaemon(True)
        self.started = Event()
        self.echodaemon = self.echoserver = self.uri = None

    def run(self):
        self.echodaemon, self.echoserver, self.uri = echoserver.main(args=["-q"], returnWithoutLooping=True)
        self.started.set()
        self.echodaemon.requestLoop(loopCondition=lambda: not self.echoserver._must_shutdown)


class TestEchoserver(unittest.TestCase):
    def setUp(self):
        self.echoserverthread = EchoServerThread()
        self.echoserverthread.start()
        self.echoserverthread.started.wait()
        self.uri = self.echoserverthread.uri

    def tearDown(self):
        self.echoserverthread.echodaemon.shutdown()
        time.sleep(0.02)
        self.echoserverthread.join()
        config.SERVERTYPE = "thread"

    def testExposed(self):
        e = Pyro4.test.echoserver.EchoServer()
        self.assertTrue(hasattr(e, "_pyroExposed"))

    def testEcho(self):
        with Pyro4.core.Proxy(self.uri) as echo:
            try:
                self.assertEqual("hello", echo.echo("hello"))
                self.assertEqual(None, echo.echo(None))
                self.assertEqual([1, 2, 3], echo.echo([1, 2, 3]))
            finally:
                echo.shutdown()

    def testError(self):
        with Pyro4.core.Proxy(self.uri) as echo:
            try:
                echo.error()
                self.fail("expected exception")
            except Exception as x:
                tb = "".join(Pyro4.util.getPyroTraceback())
                self.assertIn("Remote traceback", tb)
                self.assertIn("ValueError", tb)
                self.assertEqual("expected error from echoserver error() method", str(x))
            try:
                echo.error_with_text()
                self.fail("expected exception")
            except Exception as x:
                tb = "".join(Pyro4.util.getPyroTraceback())
                self.assertIn("Remote traceback", tb)
                self.assertIn("ValueError", tb)
                self.assertEqual("the message of the error", str(x))

    def testGenerator(self):
        with Pyro4.core.Proxy(self.uri) as echo:
            remotegenerator = echo.generator()
            self.assertIsInstance(remotegenerator, Pyro4.core._StreamResultIterator)
            next(remotegenerator)
            next(remotegenerator)
            next(remotegenerator)
            with self.assertRaises(StopIteration):
                next(remotegenerator)


if __name__ == "__main__":
    unittest.main()
