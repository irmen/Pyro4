"""
Thread pooled job queue with a fixed number of worker threads.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import sys
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


class NoFreeWorkersError(PoolError):
    pass


class Worker(Pyro4.threadutil.Thread):
    """
    Worker thread that picks jobs from the job queue and executes them.
    If it encounters the sentinel None, it will stop running.
    """

    def __init__(self, job_pool):
        super(Worker, self).__init__()
        self.daemon = True
        self.job_pool = job_pool
        self.name = "Pyro-Worker-%d " % id(self)

    def run(self):
        while True:
            job = self.job_pool.next_job()
            if job is None:
                break
            try:
                job()
                self.job_pool.job_finished()
            except Exception:
                log.exception("unhandled exception from job in worker thread %s: %s", self.name)
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
        if Pyro4.config.THREADPOOL_SIZE < 1:
            raise ValueError("threadpool size must be >= 1")
        for _ in range(Pyro4.config.THREADPOOL_SIZE):
            worker = Worker(self)
            self.pool.append(worker)
            worker.start()
        log.debug("worker pool of size %d created", self.num_workers())
        self.count_lock = Pyro4.threadutil.Lock()
        self.available_workers_sema = Pyro4.threadutil.BoundedSemaphore(self.num_workers())

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
        return "<%s.%s at 0x%x, %d workers, %d waiting jobs>" % \
               (self.__class__.__module__, self.__class__.__name__, id(self), self.num_workers(), self.waiting_jobs())

    def waiting_jobs(self):
        return self.jobs.qsize()

    def num_workers(self):
        return len(self.pool)

    def process(self, job):
        """Add the job to the general job queue."""
        if self.closed:
            raise PoolError("job queue is closed")
        if not Pyro4.config.THREADPOOL_ALLOW_QUEUE:
            if sys.version_info < (3, 2):
                success = self.available_workers_sema.acquire(blocking=False)
            else:
                timeout = max(0.5, min(5, (Pyro4.config.COMMTIMEOUT or 99999)-1))
                success = self.available_workers_sema.acquire(blocking=True, timeout=timeout)
            if not success:
                raise NoFreeWorkersError("all workers are busy")
        self.jobs.put(job)

    def next_job(self):
        if self.closed:
            return None
        return self.jobs.get()

    def job_finished(self):
        self.available_workers_sema.release()
