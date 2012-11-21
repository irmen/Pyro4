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
    """
    def __init__(self):
        self.lock = Pyro4.threadutil.Lock()
        self.pool = set()
        self.__working = 0
        self.__lastshrink = time.time()

    def fill(self, workertype, *workerargs, **workerkwargs):
        """pre-fill the pool with workers"""
        for _ in range(Pyro4.config.THREADPOOL_MINTHREADS):
            if not self.attemptSpawn(workertype, *workerargs, **workerkwargs):
                break

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

    def attemptSpawn(self, workerType, *workerArgs, **workerKwargs):
        """
        Spawns a new worker thread of the given type and adds it to the pool,
        but only if the pool is still smaller than the maximum size.
        The args are passed to the workertype constructor if a worker is actually created.
        Returns True if a worker spawned, False if the pool is already full.
        """
        with self.lock:
            if len(self.pool) < Pyro4.config.THREADPOOL_MAXTHREADS:
                worker = workerType(*workerArgs, **workerKwargs)
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
        shrunk = self.shrink()
        with self.lock:
            self.__working += number
        return shrunk

    def shrink(self):
        """Cleans up the pool: any excess idle workers are removed. Returns the number of removed workers."""
        threads = len(self.pool)
        shrunk = 0
        if threads > Pyro4.config.THREADPOOL_MINTHREADS:
            idle = threads - self.__working
            if idle > Pyro4.config.THREADPOOL_MINTHREADS and (time.time() - self.__lastshrink) > Pyro4.config.THREADPOOL_IDLETIMEOUT:
                shrunk = idle - Pyro4.config.THREADPOOL_MINTHREADS
                self.__lastshrink = time.time()
        return shrunk
