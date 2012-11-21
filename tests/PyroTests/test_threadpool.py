"""
Tests for the thread pool.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import unittest
import time
from Pyro4.threadpool import ThreadPool
import Pyro4.threadutil


class Worker(Pyro4.threadutil.Thread):
    def __init__(self, pool, name):
        Pyro4.threadutil.Thread.__init__(self)
        self.setDaemon(True)
        self.myname=name
        self.pool=pool
        self.continuerunning=True
    def run(self):
        # print("worker %s (%s) running!" % (self.getName(), self.myname))
        while self.continuerunning:
            time.sleep(0.01)
        # print("worker %s exits!" % self.getName())
        self.pool.remove(self)   # XXX for now, a worker must remove itself from the pool when it exits

class WorkerFactory(object):
    def __init__(self, pool, name):
        self.pool=pool
        self.workername=name
    def __call__(self):
        return Worker(self.pool, self.workername)


MIN_POOL_SIZE = 5
MAX_POOL_SIZE = 10
IDLE_TIMEOUT = 1

class ThreadpoolTests(unittest.TestCase):
    def setUp(self):
        Pyro4.config.THREADPOOL_MINTHREADS = MIN_POOL_SIZE
        Pyro4.config.THREADPOOL_MAXTHREADS = MAX_POOL_SIZE
        Pyro4.config.THREADPOOL_IDLETIMEOUT = IDLE_TIMEOUT
    def tearDown(self):
        Pyro4.config.reset()

    def testPoolCreation(self):
        tp = ThreadPool()
        tp.workerFactory=WorkerFactory(tp, "workername")
        self.assertEqual(0, len(tp))
        tp.fill()
        self.assertEqual(MIN_POOL_SIZE, len(tp))
        for worker in tp.pool.copy():
            worker.continuerunning=False
            worker.join()

    def testPoolGrowth(self):
        tp = ThreadPool()
        tp.workerFactory=WorkerFactory(tp, "workername")
        tp.fill()
        self.assertEqual(MIN_POOL_SIZE, len(tp))
        self.assertFalse(tp.poolCritical())
        spawned=tp.growIfNeeded()
        self.assertFalse(spawned)
        tp.updateWorking(5)
        self.assertTrue(tp.poolCritical())
        spawned=tp.growIfNeeded()
        self.assertTrue(spawned)
        self.assertEqual(6, len(tp))
        tp.updateWorking(5)  # total number of 'working' threads now sits at 10
        for _ in range(MAX_POOL_SIZE*2):
            tp.growIfNeeded()
        self.assertEqual(MAX_POOL_SIZE, len(tp))     # shouldn't grow beyond max size
        for worker in tp.pool.copy():
            worker.continuerunning=False
            worker.join()

    def testPoolShrink(self):
        Pyro4.config.THREADPOOL_MINTHREADS = MAX_POOL_SIZE
        tp = ThreadPool()
        tp.workerFactory=WorkerFactory(tp, "workername")
        tp.fill()
        self.assertFalse(tp.poolCritical())
        tp.updateWorking(MAX_POOL_SIZE)
        self.assertTrue(tp.poolCritical())
        Pyro4.config.THREADPOOL_MINTHREADS = MIN_POOL_SIZE
        self.assertEqual(MAX_POOL_SIZE, len(tp))
        self.assertTrue(tp.poolCritical())
        shrunk=tp.shrink()
        self.assertEqual(0,shrunk)
        shrunk=tp.updateWorking(-MAX_POOL_SIZE)
        self.assertFalse(tp.poolCritical())
        self.assertEqual(0,shrunk)  # shouldn't shrink because of the idle timeout
        self.assertEqual(MAX_POOL_SIZE, len(tp))

        # wait until the idle timeout has passed, and try to shrink again
        time.sleep(IDLE_TIMEOUT+0.2)
        shrunk=tp.updateWorking(0)
        self.assertEqual(MAX_POOL_SIZE-MIN_POOL_SIZE, shrunk)
        # for now we need to actually remove the idle threads ourselves
        for worker in list(tp.pool)[:shrunk]:
            worker.continuerunning=False
            worker.join()
        # the worker, when it exits, must remove itself from the thread pool
        self.assertEqual(MIN_POOL_SIZE, len(tp))
        for worker in tp.pool.copy():
            worker.continuerunning=False
            worker.join()



if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
