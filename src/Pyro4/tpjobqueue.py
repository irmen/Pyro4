"""
Thread pooled job queue that can grow and shrink its pool of worker threads.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import logging
import weakref
import time
import Pyro4.threadutil
try:
    import queue
except ImportError:
    import Queue as queue


log=logging.getLogger("Pyro4.tpjobqueue")


class NoJobAvailableError(queue.Empty):
    pass

class JobQueueError(Exception):
    pass


class Worker(Pyro4.threadutil.Thread):
    """
    Worker thread that picks jobs from the job queue and executes them.
    If it encounters None as a job, it will stop running, regardless of the pool size.
    If it encounters a lack of jobs for a short period, it will
    attempt to stop running as well in an effort to shrink the thread pool.
    """
    def __init__(self, pool):
        super(Worker, self).__init__()
        self.daemon = True
        self.pool = weakref.ref(pool)
        self.name = "Pyro-Worker-%d " % id(self)
        self.job = None  # the active job

    def run(self):
        while True:
            pool = self.pool()
            if not pool:
                break   # pool's gone, better exit
            try:
                self.job = pool.getJob()
            except NoJobAvailableError:
                # attempt to halt the worker, if the pool size permits this
                if pool.attemptHalt(self):
                    break
                else:
                    continue
            if self.job is None:
                # halt the worker, regardless of the pool size
                pool.halted(self)
                break
            else:
                pool.setBusy(self)
                try:
                    self.job()
                    pool.setIdle(self)
                except:
                    pool.halted(self, True)
                    raise



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
        self.jobs = queue.Queue()
        self.closed = False
        for _ in range(Pyro4.config.THREADPOOL_MINTHREADS):
            self.__spawnIdle()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """Close down the thread pool, signaling to all remaining worker threads to shut down."""
        count = self.workercountSafe
        for _ in range(count):
            self.jobs.put(None)  # None as a job means: terminate the worker
        log.debug("closing down, %d halt-jobs issued", count)
        self.closed = True

    def drain(self):
        """Wait till the job queue has been emptied."""
        if not self.closed:
            raise JobQueueError("can't drain a job queue that hasn't been closed yet")
        while not self.jobs.empty() and self.workercountSafe:
            # note: this loop may never end if a worker's job remains busy or blocked,
            # we simply assume all workers eventually terminate their jobs...
            time.sleep(0.1)
        time.sleep(0.05)
        if self.workercountSafe > 0:
            raise JobQueueError("there are still active workers")

    @property
    def workercount(self):
        return len(self.idle) + len(self.busy)

    @property
    def workercountSafe(self):
        with self.lock:
            return len(self.idle) + len(self.busy)

    @property
    def jobcount(self):
        return self.jobs.qsize()

    def __repr__(self):
        return "<%s.%s at 0x%x, %d idle, %d busy, %d jobs>" % \
            (self.__class__.__module__, self.__class__.__name__, id(self), len(self.idle), len(self.busy), self.jobcount)

    def process(self, job):
        """
        Add the job to the general job queue. Job is any callable object.
        If there's no idle worker available to service it, a new one is spawned
        as long as the pool size permits it.
        """
        with self.lock:
            if self.closed:
                raise JobQueueError("job queue is closed")
            self.jobs.put(job)
            if self.jobcount > 0:
                if not self.idle:
                    self.__spawnIdle()
                spawnamount = self.jobcount
                while spawnamount > 1:
                    self.__spawnIdle()
                    spawnamount -= 1

    def setIdle(self, worker):
        with self.lock:
            self.busy.remove(worker)
            self.idle.add(worker)

    def setBusy(self, worker):
        with self.lock:
            self.idle.remove(worker)
            self.busy.add(worker)

    def halted(self, worker, crashed=False):
        """Called by a worker when it halts (exits). This removes the worker from the bookkeeping."""
        with self.lock:
            self.__halted(worker)

    def __halted(self, worker):
        # Lock-free version that is used internally
        if worker in self.idle:
            self.idle.remove(worker)
        if worker in self.busy:
            self.busy.remove(worker)
        log.debug("worker halted: %s", worker.name)

    def attemptHalt(self, worker):
        """
        Called by a worker to signal it intends to halt.
        Returns true or false depending on whether the worker was actually allowed to halt.
        """
        with self.lock:
            if self.workercount > Pyro4.config.THREADPOOL_MINTHREADS:
                self.__halted(worker)
                return True
            return False

    def getJob(self):
        """
        Called by a worker to obtain a new job from the queue.
        If there's no job available in the timeout period given by the
        THREADPOOL_IDLETIMEOUT config item, NoJobAvailableError is raised.
        """
        if self.closed:
            return None
        try:
            return self.jobs.get(timeout=Pyro4.config.THREADPOOL_IDLETIMEOUT)
        except queue.Empty:
            raise NoJobAvailableError("queue is empty")

    def __spawnIdle(self):
        """
        Spawn a new idle worker if there is still room in the pool.
        (must only be called with self.lock acquired)
        """
        if self.workercount >= Pyro4.config.THREADPOOL_MAXTHREADS:
            return
        worker = Worker(self)
        self.idle.add(worker)
        log.debug("spawned new idle worker: %s", worker.name)
        worker.start()
