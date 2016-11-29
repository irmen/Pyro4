"""
Thread pool job processor with variable number of worker threads (between max/min amount).

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import time
import logging
import Pyro4.threadutil
import Pyro4.util

__all__ = ["PoolError", "NoFreeWorkersError", "Pool"]

log = logging.getLogger("Pyro4.threadpool")


class PoolError(Exception):
    pass


class NoFreeWorkersError(PoolError):
    pass


class Worker(Pyro4.threadutil.Thread):
    def __init__(self, pool):
        super(Worker, self).__init__()
        self.daemon = True
        self.name = "Pyro-Worker-%d " % id(self)
        self.job_available = Pyro4.threadutil.Event()
        self.job = None
        self.pool = pool

    def process(self, job):
        self.job = job
        self.job_available.set()

    def run(self):
        while True:
            self.job_available.wait()
            self.job_available.clear()
            if self.job is None:
                break
            try:
                self.job()
            except Exception:
                log.exception("unhandled exception from job in worker thread %s: %s", self.name)
            self.job = None
            self.pool.notify_done(self)
        self.pool = None


class Pool(object):
    """
    A job processing pool that is using a pool of worker threads.
    The amount of worker threads in the pool is configurable and scales between min/max size.
    """
    def __init__(self):
        if Pyro4.config.THREADPOOL_SIZE < 1 or Pyro4.config.THREADPOOL_SIZE_MIN < 1:
            raise ValueError("threadpool sizes must be greater than zero")
        if Pyro4.config.THREADPOOL_SIZE_MIN > Pyro4.config.THREADPOOL_SIZE:
            raise ValueError("minimum threadpool size must be less than or equal to max size")
        self.idle = set()
        self.busy = set()
        self.closed = False
        for _ in range(Pyro4.config.THREADPOOL_SIZE_MIN):
            worker = Worker(self)
            self.idle.add(worker)
            worker.start()
        log.debug("worker pool created with initial size %d", self.num_workers())
        self.count_lock = Pyro4.threadutil.Lock()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if not self.closed:
            log.debug("closing down")
            for w in self.busy:
                w.process(None)
            for w in self.idle:
                w.process(None)
            self.closed = True
            time.sleep(0.1)
            idle, self.idle = self.idle, set()
            busy, self.busy = self.busy, set()
            # check if the threads that are joined are not the current thread,
            # otherwise Python 2.x crashes with "cannot join current thread".
            current_thread = Pyro4.threadutil.current_thread()
            while idle:
                p = idle.pop()
                if p is not current_thread:
                    p.join(timeout=0.1)
            while busy:
                p = busy.pop()
                if p is not current_thread:
                    p.join(timeout=0.1)

    def __repr__(self):
        return "<%s.%s at 0x%x; %d busy workers; %d idle workers>" % \
               (self.__class__.__module__, self.__class__.__name__, id(self), len(self.busy), len(self.idle))

    def num_workers(self):
        return len(self.busy) + len(self.idle)

    def process(self, job):
        if self.closed:
            raise PoolError("job queue is closed")
        if self.idle:
            worker = self.idle.pop()
        elif self.num_workers() < Pyro4.config.THREADPOOL_SIZE:
            worker = Worker(self)
            worker.start()
        else:
            raise NoFreeWorkersError("no free workers available, increase thread pool size")
        self.busy.add(worker)
        worker.process(job)
        log.debug("worker counts: %d busy, %d idle", len(self.busy), len(self.idle))

    def notify_done(self, worker):
        if worker in self.busy:
            self.busy.remove(worker)
        if self.closed:
            worker.process(None)
            return
        if len(self.idle) >= Pyro4.config.THREADPOOL_SIZE_MIN:
            worker.process(None)
        else:
            self.idle.add(worker)
        log.debug("worker counts: %d busy, %d idle", len(self.busy), len(self.idle))
