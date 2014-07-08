"""
Thread pooled job queue with a fixed number of worker threads.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import logging
import Pyro4.threadutil
import Pyro4.util

try:
    import queue
except ImportError:
    import Queue as queue

__all__ = ["PoolError", "Pool"]

log = logging.getLogger("Pyro4.threadpool")


class PoolError(Exception):
    pass


class Worker(Pyro4.threadutil.Thread):
    """
    Worker thread that picks jobs from the job queue and executes them.
    If it encounters the sentinel None, it will stop running.
    """

    def __init__(self, jobs):
        super(Worker, self).__init__()
        self.daemon = True
        self.jobs = jobs
        self.name = "Pyro-Worker-%d " % id(self)

    def run(self):
        for job in self.jobs:
            if job is None:
                break
            try:
                job()
            except Exception:
                tb = "".join(Pyro4.util.getPyroTraceback())
                log.error("unhandled exception from job in worker thread %s: %s", self.name, tb)
                # we continue running, just pick another job from the queue


class Pool(object):
    """
    A job queue that is serviced by a pool of worker threads.
    The size of the pool is configurable but stays fixed.
    """

    def __init__(self):
        self.pool = []
        self.jobs = queue.Queue()
        self.closed = False
        for _ in range(Pyro4.config.THREADPOOL_SIZE):
            worker = Worker(self.jobs_generator())
            self.pool.append(worker)
            worker.start()
        log.debug("worker pool of size %d created", self.num_workers())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """Close down the thread pool, signaling to all remaining worker threads to shut down."""
        for _ in range(self.num_workers()):
            self.jobs.put(None)  # None as a job means: terminate the worker
        log.debug("closing down, %d halt-jobs issued", self.num_workers())
        self.closed = True
        self.pool = []

    def __repr__(self):
        return "<%s.%s at 0x%x, %d workers, %d jobs>" % \
               (self.__class__.__module__, self.__class__.__name__, id(self), self.num_workers(), self.num_jobs())

    def num_jobs(self):
        return self.jobs.qsize()

    def num_workers(self):
        return len(self.pool)

    def process(self, job):
        """
        Add the job to the general job queue. Job is any callable object.
        """
        if self.closed:
            raise PoolError("job queue is closed")
        self.jobs.put(job)

    def jobs_generator(self):
        """generator that yields jobs from the queue"""
        while not self.closed:
            yield self.jobs.get()  # this is a thread-safe operation (on queue) so we don't need our own locking
