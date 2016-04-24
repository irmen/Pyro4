"""
Tests for the thread pool.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement, print_function
import time
import random
import unittest
from Pyro4.socketserver.threadpool import Pool, PoolError, NoFreeWorkersError
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
        pass

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
            self.assertEqual(0, p.waiting_jobs())

    def testThreadpoolQueue(self):
        class Job2(object):
            def __init__(self, name="unnamed"):
                self.name = name

            def __call__(self):
                time.sleep(0.7)
        try:
            Pyro4.config.THREADPOOL_ALLOW_QUEUE = True
            Pyro4.config.COMMTIMEOUT = 0.1
            with Pool() as p:
                for i in range(1 + Pyro4.config.THREADPOOL_SIZE * 2):
                    p.process(Job2(str(i)))
                time.sleep(2)
                self.assertEqual(0, p.waiting_jobs(), "queue must be finished in under two seconds")
        finally:
            Pyro4.config.THREADPOOL_ALLOW_QUEUE = False
            Pyro4.config.COMMTIMEOUT = 0

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
        # test that after closing a job queue, no more new jobs are taken from the queue, and some other stuff
        with Pool() as p:
            for i in range(Pyro4.config.THREADPOOL_SIZE):
                p.process(Job(str(i + 1)))
        with self.assertRaises(PoolError):
            p.process(Job(1))  # must not allow new jobs after closing
        self.assertTrue(p.waiting_jobs() > 1)
        time.sleep(JOB_TIME * 1.1)
        jobs_left = p.waiting_jobs()
        time.sleep(JOB_TIME * 1.1)  # wait till jobs finish and a new one *might* be taken off the queue
        self.assertEqual(jobs_left, p.waiting_jobs(), "may not process new jobs after close")


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
