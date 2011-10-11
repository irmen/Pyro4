"""
Generic thread pool implementation that can grow and shrink.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import time
import Pyro4.threadutil


class ThreadPool(object):
    """
    A pool of threads that can grow and shrink between limits set by the
    THREADPOOL_MINTHREADS and THREADPOOL_MAXTHREADS config items.
    Make sure to set the ``workerFactory`` attribute after creation,
    to a callable that returns a worker thread object.

    ....this class didn't turn out to be as nice as I wanted; you still need to do
    quite a lot of work yourself in the worker threads or the controlling code.
    Worker threads need to call updateWorking with +1 or -1 when they start or finish work,
    and controlling code needs to call growIfNeeded when processing tasks. Also, when a worker
    thread exits, it needs to call remove by itself to actually remove it from the pool.
    Maybe I'll refactor this thing in the future.
    """
    def __init__(self):
        self.lock = Pyro4.threadutil.Lock()
        self.pool = set()
        self.workerFactory=None   # you must set this after creation
        self.__working = 0
        self.__lastshrink = time.time()

    def __len__(self):
        return len(self.pool)

    def __repr__(self):
        return "<%s.%s at 0x%x, poolsize %s>" % (self.__class__.__module__, self.__class__.__name__, id(self), len(self.pool))

    def fill(self):
        """pre-fill the pool with workers"""
        for _ in range(Pyro4.config.THREADPOOL_MINTHREADS):
            if not self.attemptSpawn():
                break

    def growIfNeeded(self):
        """If there are no more idle workers in the pool, spawn a new one, and return True. Otherwise, return False."""
        if self.poolCritical():
            return self.attemptSpawn()

    def attemptRemove(self, member):
        """
        Removes a member from the pool but only if it is still larger than the minimum size.
        Returns True if it was removed, False otherwise.
        """
        with self.lock:
            if len(self.pool) > Pyro4.config.THREADPOOL_MINTHREADS:
                self.pool.remove(member)
                return True
            return False

    def remove(self, member):
        """Removes a member from the pool regardless of the current pool size"""
        with self.lock:
            try:
                self.pool.remove(member)
            except KeyError:
                pass

    def attemptSpawn(self):
        """
        Spawns a new worker thread of the given type and adds it to the pool,
        but only if the pool is still smaller than the maximum size.
        Returns True if a worker spawned, False if the pool is already full.
        """
        with self.lock:
            if len(self.pool) < Pyro4.config.THREADPOOL_MAXTHREADS:
                worker = self.workerFactory()
                self.pool.add(worker)
                worker.start()
                return True
            return False

    def poolCritical(self):
        """Determine if the pool has run out of idle workers"""
        idle = len(self.pool) - self.__working
        return idle <= 0

    def updateWorking(self, number):
        """
        Updates the number of 'busy' workers in the pool.
        Should be called with +1 by a worker thread when it is starting to work, and with -1 once it stopped working.
        The number of 'busy' workers is needed to determine of the pool should be grown or shrunk.
        This method returns the number of workers removed in case a pool shrink occurred.
        """
        with self.lock:
            self.__working += number
        return self.shrink()

    def shrink(self):
        """Cleans up the pool: any excess idle workers are removed. Returns the number of removed workers."""
        threads = len(self.pool)
        shrunk = 0
        if threads > Pyro4.config.THREADPOOL_MINTHREADS:
            idle = threads - self.__working
            if idle > Pyro4.config.THREADPOOL_MINTHREADS and (time.time() - self.__lastshrink) > Pyro4.config.THREADPOOL_IDLETIMEOUT:
                shrunk = idle - Pyro4.config.THREADPOOL_MINTHREADS
                # XXX hmm, something should actually remove the idle threads from the pool here ..... instead of depending on the user to do it....
                self.__lastshrink = time.time()
        return shrunk
