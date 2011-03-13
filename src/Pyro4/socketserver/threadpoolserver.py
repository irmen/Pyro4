"""
Socket server based on a worker thread pool. Doesn't use select.

Uses a single worker thread per client connection.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong.
irmen@razorvine.net - http://www.razorvine.net/python/Pyro
"""

from __future__ import with_statement
import socket, logging, sys
try:
    import queue
except ImportError:
    import Queue as queue
import time, os
from Pyro4.socketutil import SocketConnection, createSocket
from Pyro4.errors import ConnectionClosedError, PyroError
import Pyro4.config
from Pyro4 import threadutil

log=logging.getLogger("Pyro.socketserver.threadpool")

class SocketWorker(threadutil.Thread):
    """worker thread to process requests"""
    def __init__(self, server, callback):
        super(SocketWorker,self).__init__()
        self.setDaemon(True)
        self.server=server
        self.callback=callback
        if os.name=="java":
            # jython names every thread 'Thread', so we improve that a little
            self.setName("Thread-%d"%id(self))
    def run(self):
        self.running=True
        try:
            log.debug("new worker %s", self.getName())
            while self.running: # loop over all connections in the queue
                self.csock,self.caddr = self.server.workqueue.get()
                if self.csock is None and self.caddr is None:
                    # this was a 'stop' sentinel
                    self.running=False
                    break
                log.debug("worker %s got a client connection %s", self.getName(), self.caddr)
                self.csock=SocketConnection(self.csock)
                if self.handleConnection(self.csock):
                    self.server.threadpool.updateWorking(1)  # tell the pool we're working
                    try:
                        while self.running:   # loop over all requests during a single connection
                            try:
                                self.callback.handleRequest(self.csock)
                            except (socket.error,ConnectionClosedError):
                                # client went away.
                                log.debug("worker %s client disconnected %s", self.getName(), self.caddr)
                                break
                        self.csock.close()
                    finally:
                        # make sure we tell the pool that we are no longer working
                        self.server.threadpool.updateWorking(-1)
        # Note: we don't swallow exceptions here anymore because @Pyro4.callback doesn't
        #       do anything anymore if we do (the re-raised exception would be swallowed...)
        #except Exception:
        #    exc_type, exc_value, _ = sys.exc_info()
        #    log.warn("swallow exception in worker %s: %s %s",self.getName(),exc_type,exc_value)
        finally:
            self.server.threadpool.remove(self)
            log.debug("stopping worker %s", self.getName())
    def handleConnection(self,conn):
        try:
            if self.callback.handshake(conn):
                return True
        except (socket.error, PyroError):
            x=sys.exc_info()[1]
            log.warn("error during connect: %s",x)
            conn.close()
        return False
                    
class ThreadPool(set):
    lock=threadutil.Lock()
    def __init__(self, server, callback):
        self.__server=server
        self.__callback=callback
        self.__working=0
        self.__lastshrink=time.time()
    def attemptRemove(self, member):
        with self.lock:
            if len(self)>Pyro4.config.THREADPOOL_MINTHREADS:
                super(ThreadPool,self).remove(member)
                return True
            return False
    def remove(self, member):
        with self.lock:
            try:
                super(ThreadPool,self).remove(member)
            except KeyError:
                pass
    def attemptSpawn(self):
        with self.lock:
            if len(self)<Pyro4.config.THREADPOOL_MAXTHREADS:
                worker=SocketWorker(self.__server, self.__callback)
                self.add(worker)
                worker.start()
                return True
            return False
    def poolCritical(self):
        idle=len(self)-self.__working
        return idle<=0
    def updateWorking(self, number):
        self.shrink()
        with self.lock:
            self.__working+=number
    def shrink(self):
        threads=len(self)
        if threads>Pyro4.config.THREADPOOL_MINTHREADS:
            idle=threads-self.__working
            if idle>Pyro4.config.THREADPOOL_MINTHREADS and (time.time()-self.__lastshrink)>Pyro4.config.THREADPOOL_IDLETIMEOUT:
                for _ in range(idle-Pyro4.config.THREADPOOL_MINTHREADS):
                    self.__server.workqueue.put((None,None)) # put a 'stop' sentinel in the worker queue to kill a worker
                self.__lastshrink=time.time()
                    
class SocketServer_Threadpool(object):
    """transport server for socket connections, worker thread pool version."""
    def __init__(self, callbackObject, host, port, timeout=None):
        log.info("starting thread pool socketserver")
        self.sock=None
        self.sock=createSocket(bind=(host,port), timeout=timeout, noinherit=True)
        self._socketaddr=self.sock.getsockname()
        if self._socketaddr[0].startswith("127."):
            if host is None or host.lower()!="localhost" and not host.startswith("127."):
                log.warn("weird DNS setup: %s resolves to localhost (127.x.x.x)",host)
        host=host or self._socketaddr[0]
        port=port or self._socketaddr[1]
        self.locationStr="%s:%d" % (host,port)
        self.threadpool=ThreadPool(self, callbackObject)
        self.workqueue=queue.Queue()
        for _ in range(Pyro4.config.THREADPOOL_MINTHREADS):
            self.threadpool.attemptSpawn()
        log.info("%d worker threads started", len(self.threadpool))
    def __del__(self):
        if self.sock is not None:
            self.sock.close()

    def requestLoop(self, loopCondition=lambda:True):
        log.debug("threadpool server requestloop")
        while (self.sock is not None) and loopCondition():
            try:
                self.handleRequests(None)
            except socket.error:
                if not loopCondition():
                    # swallow the socket error if loop terminates anyway
                    # this can occur if we are asked to shutdown, socket can be invalid then
                    break
                else:
                    raise
            except KeyboardInterrupt:
                log.debug("stopping on break signal")
                break
        log.debug("threadpool server exits requestloop")
    def handleRequests(self, eventsockets):
        try:
            # we only react on events on our own server socket.
            # all other (client) sockets are owned by their individual threads.
            csock, caddr=self.sock.accept()
            log.debug("connection from %s",caddr)
            if Pyro4.config.COMMTIMEOUT:
                csock.settimeout(Pyro4.config.COMMTIMEOUT)
            if self.threadpool.poolCritical():
                self.threadpool.attemptSpawn()
            self.workqueue.put((csock,caddr))
        except socket.timeout:
            pass  # just continue the loop on a timeout on accept

    def close(self, joinWorkers=True): 
        log.debug("closing threadpool server")
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock=None
        for worker in self.threadpool.copy():
            worker.running=False
            csock=getattr(worker,"csock",None)
            if csock:
                csock.close()    # terminate socket that the worker might be listening on
            if self.workqueue is not None:
                self.workqueue.put((None,None)) # put a 'stop' sentinel in the worker queue
        while joinWorkers:
            try:
                worker=self.threadpool.pop()
            except KeyError:
                break
            else:
                worker.join()

    def fileno(self):
        return self.sock.fileno()
    def sockets(self):
        # the server socket is all we care about, all client sockets are running in their own threads 
        return [self.sock]

    def pingConnection(self):
        """bit of a hack to trigger a blocking server to get out of the loop, useful at clean shutdowns"""
        try:
            sock=createSocket(connect=self._socketaddr)
            if sys.version_info<(3,0): 
                sock.send("!"*16)
            else:
                sock.send(bytes([1]*16))
            sock.close()
        except socket.error:
            pass

