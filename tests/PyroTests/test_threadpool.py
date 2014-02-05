"""
Tests for the thread pool.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement, print_function
import time
import random
from Pyro4.socketserver.threadpool import Pool, PoolError
import Pyro4.threadutil
from testsupport import unittest

JOB_TIME = 0.2


class Job(object):
    def __init__(self, name="unnamed"):
        self.name=name
    def __call__(self):
        # print("Job() '%s'" % self.name)
        time.sleep(JOB_TIME - random.random()/10.0)
        # print("Job() '%s' done" % self.name)


class PoolTests(unittest.TestCase):
    def setUp(self):
        pass
    def tearDown(self):
        Pyro4.config.reset()

    def testCreate(self):
        with Pool() as jq:
            _=repr(jq)
        self.assertTrue(jq.closed)

    def testSingle(self):
        with Pool() as p:
            job = Job()
            p.process(job)
            time.sleep(0.02)  # let it pick up the job
            self.assertEqual(0, p.num_jobs())

    def testMany(self):
        class Job2(object):
            def __init__(self, name="unnamed"):
                self.name=name
            def __call__(self):
                time.sleep(0.01)
        with Pool() as p:
            for i in range(1+Pyro4.config.THREADPOOL_SIZE*100):
                p.process(Job2(str(i)))
            time.sleep(2)
            self.assertEqual(0, p.num_jobs(), "queue must be finished in under two seconds")

    def testClose(self):
        # test that after closing a job queue, no more new jobs are taken from the queue, and some other stuff
        with Pool() as p:
            for i in range(2*Pyro4.config.THREADPOOL_SIZE):
                p.process(Job(str(i+1)))
            self.assertTrue(p.num_jobs() > 1)

        self.assertRaises(PoolError, p.process, Job(1))  # must not allow new jobs after closing
        self.assertTrue(p.num_jobs() > 1)
        time.sleep(JOB_TIME*1.1)
        jobs_left = p.num_jobs()
        time.sleep(JOB_TIME*1.1)   # wait till jobs finish and a new one *might* be taken off the queue
        self.assertEqual(jobs_left, p.num_jobs(), "may not process new jobs after close")


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
