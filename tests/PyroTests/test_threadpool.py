"""
Tests for the thread pool.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import print_function
import time
import random
import unittest
from Pyro4.socketserver.threadpool import Pool, PoolError, NoFreeWorkersError
from Pyro4.socketserver.threadpoolserver import SocketServer_Threadpool
import Pyro4.socketutil
import Pyro4.threadutil


JOB_TIME = 0.2


class Job(object):
    def __init__(self, name="unnamed"):
        self.name = name

    def __call__(self):
        time.sleep(JOB_TIME - random.random() / 10.0)


class SlowJob(object):
    def __init__(self, name="unnamed"):
        self.name = name

    def __call__(self):
        time.sleep(5*JOB_TIME - random.random() / 10.0)


class PoolTests(unittest.TestCase):
    def setUp(self):
        Pyro4.config.THREADPOOL_SIZE_MIN = 2
        Pyro4.config.THREADPOOL_SIZE = 4

    def tearDown(self):
        Pyro4.config.reset()

    def testCreate(self):
        with Pool() as jq:
            _ = repr(jq)
        self.assertTrue(jq.closed)

    def testSingle(self):
        with Pool() as p:
            job = Job()
            p.process(job)
            time.sleep(0.02)  # let it pick up the job
            self.assertEqual(1, len(p.busy))

    def testAllBusy(self):
        try:
            Pyro4.config.COMMTIMEOUT = 0.2
            with Pool() as p:
                for i in range(Pyro4.config.THREADPOOL_SIZE):
                    p.process(SlowJob(str(i+1)))
                # putting one more than the number of workers should raise an error:
                with self.assertRaises(NoFreeWorkersError):
                    p.process(SlowJob("toomuch"))
        finally:
            Pyro4.config.COMMTIMEOUT = 0.0

    def testClose(self):
        with Pool() as p:
            for i in range(Pyro4.config.THREADPOOL_SIZE):
                p.process(Job(str(i + 1)))
        with self.assertRaises(PoolError):
            p.process(Job(1))  # must not allow new jobs after closing
        self.assertEqual(0, len(p.busy))
        self.assertEqual(0, len(p.idle))

    def testScaling(self):
        with Pool() as p:
            for i in range(Pyro4.config.THREADPOOL_SIZE_MIN-1):
                p.process(Job("x"))
            self.assertEqual(1, len(p.idle))
            self.assertEqual(Pyro4.config.THREADPOOL_SIZE_MIN-1, len(p.busy))
            p.process(Job("x"))
            self.assertEqual(0, len(p.idle))
            self.assertEqual(Pyro4.config.THREADPOOL_SIZE_MIN, len(p.busy))
            # grow until no more free workers
            while True:
                try:
                    p.process(Job("x"))
                except NoFreeWorkersError:
                    break
            self.assertEqual(0, len(p.idle))
            self.assertEqual(Pyro4.config.THREADPOOL_SIZE, len(p.busy))
            # wait till jobs are done and check ending situation
            time.sleep(JOB_TIME*1.5)
            self.assertEqual(0, len(p.busy))
            self.assertEqual(Pyro4.config.THREADPOOL_SIZE_MIN, len(p.idle))


class ServerCallback(Pyro4.core.Daemon):
    def __init__(self):
        self.received_denied_reasons = []

    def _handshake(self, connection, denied_reason=None):
        self.received_denied_reasons.append(denied_reason)  # store the denied reason
        return True

    def handleRequest(self, connection):
        time.sleep(0.05)

    def _housekeeping(self):
        pass


class ThreadPoolServerTests(unittest.TestCase):
    def setUp(self):
        Pyro4.config.THREADPOOL_SIZE_MIN = 1
        Pyro4.config.THREADPOOL_SIZE = 1
        Pyro4.config.POLLTIMEOUT = 0.5
        Pyro4.config.COMMTIMEOUT = 0.5

    def tearDown(self):
        Pyro4.config.reset()

    def testServerPoolFull(self):
        port = Pyro4.socketutil.findProbablyUnusedPort()
        serv = SocketServer_Threadpool()
        daemon = ServerCallback()
        serv.init(daemon, "localhost", port)
        serversock = serv.sock.getsockname()
        csock1 = Pyro4.socketutil.createSocket(connect=serversock)
        csock2 = Pyro4.socketutil.createSocket(connect=serversock)
        try:
            serv.events([serv.sock])
            time.sleep(0.2)
            self.assertEqual([None], daemon.received_denied_reasons)
            serv.events([serv.sock])
            time.sleep(0.2)
            self.assertEqual(2, len(daemon.received_denied_reasons))
            self.assertIn("no free workers, increase server threadpool size", daemon.received_denied_reasons)
        finally:
            csock1.close()
            csock2.close()
            serv.shutdown()


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
