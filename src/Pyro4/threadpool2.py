"""
Generic thread pool implementation that can grow and shrink.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import logging
import weakref
import os
import Pyro4.threadutil
import Pyro4.errors
try:
    import queue
except ImportError:
    import Queue as queue


log=logging.getLogger("Pyro4.threadpool")


class PoolFullError(Pyro4.errors.PyroError):
    pass


class HaltingJob(object):
    pass


class Worker(Pyro4.threadutil.Thread):
    def __init__(self, pool):
        super(Worker, self).__init__()
        self.daemon = True
        self.jobs = queue()
        self.pool = weakref.ref(pool)
        if os.name=="java":
            # jython names every thread 'Thread', so we improve that a little
            self.setName("Thread-%d"%id(self))

    def assign(self, job):
        self.jobs.put(job)

    def halt(self):
        self.jobs.put(HaltingJob())

    def run(self):
        while True:
            job = self.jobs.get()
            if job is HaltingJob:
                break
            else:
                pool = self.pool()
                if pool:
                    pool.setBusy(self)
                try:
                    job()
                finally:
                    if pool:
                        pool.setIdle(self)


class ThreadPooledJobQueue(object):
    """
    A job queue that is serviced by a pool of worker threads that grows or
    shrings as demanded by the work load, between limits set by the
    THREADPOOL_MINTHREADS and THREADPOOL_MAXTHREADS config items.
    """
    def __init__(self):
        self.lock = Pyro4.threadutil.Lock()
        self.idle = set()
        self.busy = set()
        self.jobs = queue()

    @property
    def size(self):
        return len(self.idle) + len(self.busy)

    def __repr__(self):
        return "<%s.%s at 0x%x, %d idle, %d working, %d pending jobs>" % (self.__class__.__module__, self.__class__.__name__, id(self), len(self.idle), len(self.working), self.jobs.qsize())

    def process(self, job):
        """
        Add the job to the general job queue.
        If there's no idle worker to service it, a new one is spawned.
        """
        with self.lock:
            if not self.idle:
                try:
                    worker = self._spawn()
                    self.idle.add(worker)
                except PoolFullError:
                    pass
        self.jobs.put(job)

    def _spawn(self):
        """Spawn a new worker if there is still room in the pool."""
        if self.size < Pyro4.config.THREADPOOL_MAXTHREADS:
            raise PoolFullError()
        return Worker(self)

    def setIdle(self, worker):
        with self.lock:
            print "worker -> idle:", worker # XXX
            self.busy.remove(worker)
            self.idle.add(worker)
            self._shrink()

    def setBusy(self, worker):
        with self.lock:
            print "worker -> busy:", worker # XXX
            self.idle.remove(worker)
            self.busy.add(worker)

    def _shrink(self):
        """Attempt to shrink the pool (remove idle workers until pool reaches minimum size)"""
        while self.size > Pyro4.config.THREADPOOL_MINTHREADS and self.idle:
            worker = self.idle.pop()
            worker.halt()
            worker.join()
