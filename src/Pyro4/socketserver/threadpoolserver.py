"""
Socket server based on a worker thread pool. Doesn't use select.

Uses a single worker thread per client connection.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import socket, logging, sys, os
try:
    import queue
except ImportError:
    import Queue as queue
from Pyro4 import socketutil, threadutil, errors
import Pyro4.threadpool

log=logging.getLogger("Pyro4.socketserver.threadpool")


class SocketWorker(threadutil.Thread):
    """worker thread to process requests"""
    def __init__(self, server, daemon):
        super(SocketWorker, self).__init__()
        self.setDaemon(True)
        self.server=server
        self.callbackDaemon=daemon
        if os.name=="java":
            # jython names every thread 'Thread', so we improve that a little
            self.setName("Thread-%d"%id(self))

    def run(self):
        self.running=True
        try:
            while self.running:  # loop over all connections in the queue
                self.csock, self.caddr = self.server.workqueue.get()
                if self.csock is None and self.caddr is None:
                    # this was a 'stop' sentinel
                    self.running=False
                    break
                self.csock=socketutil.SocketConnection(self.csock)
                if self.handleConnection(self.csock):
                    shrunk = self.server.threadpool.updateWorking(1)  # tell the pool we're working
                    self.processPoolShrink(shrunk)
                    try:
                        while self.running:   # loop over all requests during a single connection
                            try:
                                self.callbackDaemon.handleRequest(self.csock)
                            except (socket.error, errors.ConnectionClosedError):
                                # client went away.
                                log.debug("worker %s client disconnected %s", self.getName(), self.caddr)
                                break
                            except errors.SecurityError:
                                log.debug("worker %s client security error %s", self.getName(), self.caddr)
                                break
                        self.csock.close()
                    finally:
                        # make sure we tell the pool that we are no longer working
                        shrunk = self.server.threadpool.updateWorking(-1)
                        self.processPoolShrink(shrunk)
        # Note: we don't swallow exceptions here anymore because @Pyro4.callback doesn't
        #       do anything anymore if we do (the re-raised exception would be swallowed...)
        #except Exception:
        #    exc_type, exc_value, _ = sys.exc_info()
        #    log.warn("swallow exception in worker %s: %s %s", self.getName(), exc_type, exc_value)
        finally:
            self.server.threadpool.remove(self)
            log.debug("stopping worker %s", self.getName())

    def processPoolShrink(self, amount):
        # for every worker removed from the pool, put a 'stop' sentinel in the worker queue to kill a worker thread.
        for _ in range(amount):
            self.server.workqueue.put((None, None))

    def handleConnection(self, conn):
        try:
            if self.callbackDaemon._handshake(conn):
                return True
        except (socket.error, errors.PyroError):
            x=sys.exc_info()[1]
            log.warn("error during connect: %s", x)
            conn.close()
        return False


class SocketWorkerFactory(object):
    def __init__(self, server, daemon):
        self.server=server
        self.daemon=daemon
    def __call__(self):
        return SocketWorker(self.server, self.daemon)


class SocketServer_Threadpool(object):
    """transport server for socket connections, worker thread pool version."""
    def init(self, daemon, host, port, unixsocket=None):
        log.info("starting thread pool socketserver")
        self.daemon = daemon
        self.sock=None
        bind_location=unixsocket if unixsocket else (host,port)
        self.sock=socketutil.createSocket(bind=bind_location, reuseaddr=Pyro4.config.SOCK_REUSE, timeout=Pyro4.config.COMMTIMEOUT, noinherit=True)
        self._socketaddr=self.sock.getsockname()
        if self._socketaddr[0].startswith("127."):
            if host is None or host.lower()!="localhost" and not host.startswith("127."):
                log.warn("weird DNS setup: %s resolves to localhost (127.x.x.x)", host)
        if unixsocket:
            self.locationStr="./u:"+unixsocket
        else:
            host=host or self._socketaddr[0]
            port=port or self._socketaddr[1]
            self.locationStr="%s:%d" % (host, port)
        self.workqueue=queue.Queue()
        self.threadpool=Pyro4.threadpool.ThreadPool()
        self.threadpool.workerFactory=SocketWorkerFactory(self, self.daemon)
        self.threadpool.fill()
        log.info("%d worker threads started", len(self.threadpool))

    def __del__(self):
        if self.sock is not None:
            self.sock.close()

    def __repr__(self):
        return "<%s on %s, poolsize %d, %d queued>" % (self.__class__.__name__, self.locationStr,
            len(self.threadpool), self.workqueue.qsize())

    def loop(self, loopCondition=lambda: True):
        log.debug("threadpool server requestloop")
        while (self.sock is not None) and loopCondition():
            try:
                self.events([self.sock])
            except socket.error:
                x=sys.exc_info()[1]
                err=getattr(x, "errno", x.args[0])
                if not loopCondition():
                    # swallow the socket error if loop terminates anyway
                    # this can occur if we are asked to shutdown, socket can be invalid then
                    break
                if err in socketutil.ERRNO_RETRIES:
                    continue
                else:
                    raise
            except KeyboardInterrupt:
                log.debug("stopping on break signal")
                break
        log.debug("threadpool server exits requestloop")

    def events(self, eventsockets):
        """used for external event loops: handle events that occur on one of the sockets of this server"""
        # we only react on events on our own server socket.
        # all other (client) sockets are owned by their individual threads.
        assert self.sock in eventsockets
        try:
            csock, caddr=self.sock.accept()
            log.debug("connection from %s", caddr)
            if Pyro4.config.COMMTIMEOUT:
                csock.settimeout(Pyro4.config.COMMTIMEOUT)
            self.threadpool.growIfNeeded()
            self.workqueue.put((csock, caddr))
        except socket.timeout:
            pass  # just continue the loop on a timeout on accept

    def close(self, joinWorkers=True):
        log.debug("closing threadpool server")
        if self.sock:
            sockname=None
            try:
                sockname=self.sock.getsockname()
            except socket.error:
                pass
            try:
                self.sock.close()
                if type(sockname) is str:
                    # it was a Unix domain socket, remove it from the filesystem
                    if os.path.exists(sockname):
                        os.remove(sockname)
            except Exception:
                pass
            self.sock=None
        if self.workqueue is not None:
            for _ in range(len(self.threadpool)):
                self.workqueue.put((None, None))  # put a 'stop' sentinel in the worker queue for every worker
        for worker in self.threadpool.pool.copy():
            worker.running=False
            csock=getattr(worker, "csock", None)
            if csock:
                try:
                    csock.sock.shutdown(socket.SHUT_RDWR)
                except (EnvironmentError, socket.error):
                    pass
                csock.close()
        while joinWorkers:
            try:
                worker=self.threadpool.pool.pop()
            except KeyError:
                break
            else:
                worker.join()

    @property
    def sockets(self):
        # the server socket is all we care about, all client sockets are running in their own threads
        return [self.sock]

    def wakeup(self):
        """bit of a hack to trigger a blocking server to get out of the loop, useful at clean shutdowns"""
        try:
            sock=socketutil.createSocket(connect=self._socketaddr)
            if sys.version_info<(3, 0):
                sock.send("!"*16)
            else:
                sock.send(bytes([1]*16))
            sock.close()
        except socket.error:
            pass
