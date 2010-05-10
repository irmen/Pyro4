######################################################################
#
#  socket server based on a worker thread pool. Doesn't use select.
#
#  Pyro - Python Remote Objects.  Copyright by Irmen de Jong.
#  irmen@razorvine.net - http://www.razorvine.net/python/Pyro
#
######################################################################

import os, Queue
import threading, socket, select
import logging
from Pyro.socketutil import SocketConnection, createSocket
from Pyro.errors import ConnectionClosedError, PyroError

if os.name=="java":
    # Jython needs a select wrapper.
    selectfunction=select.cpython_compatible_select #@UndefinedVariable (pydev)
else:
    selectfunction=select.select

log=logging.getLogger("Pyro.socketserver.threadpool")

class SocketWorker(threading.Thread):
    """worker thread to process requests"""
    def __init__(self, server, callback):
        super(SocketWorker,self).__init__()
        self.setDaemon(True)
        self.server=server
        self.callback=callback
    def run(self):
        self.running=True
        try:
            log.debug("worker %s waiting for work", self.getName())
            while self.running: # loop over all connections in the queue
                self.csock,self.caddr = self.server.workqueue.get()
                if self.csock is None and self.caddr is None:
                    # this was a 'stop' sentinel
                    self.running=False
                    break
                log.debug("worker %s got a client connection %s", self.getName(), self.caddr)
                self.csock=SocketConnection(self.csock)
                if self.handleConnection(self.csock):
                    while self.running:   # loop over all requests during a single connection
                        try:
                            self.callback.handleRequest(self.csock)
                        except (socket.error,ConnectionClosedError):
                            # client went away.
                            log.debug("worker %s client disconnected %s", self.getName(), self.caddr)
                            break
                    self.csock.close()
                    del self.csock
        finally:
            self.server.threadpool.remove(self)
        log.debug("worker %s stopping", self.getName())
    def handleConnection(self,conn):
        try:
            if self.callback.handshake(conn):
                return True
        except (socket.error, PyroError), x:
            log.warn("error during connect: %s",x)
            conn.close()
        return False
                    
class SocketServer(object):
    """transport server for socket connections, worker thread pool version."""
    def __init__(self, callbackObject, host, port, timeout=None):
        log.info("starting thread pool socketserver")
        self.sock=createSocket(bind=(host,port), timeout=timeout)
        self._socketaddr=self.sock.getsockname()
        if self._socketaddr[0].startswith("127."):
            if host is None or host.lower()!="localhost" and not host.startswith("127."):
                log.warn("weird DNS setup: %s resolves to localhost (127.x.x.x)",host)
        host=host or self._socketaddr[0]
        port=port or self._socketaddr[1]
        self.locationStr="%s:%d" % (host,port)
        numthreads=10    # XXX configurable, but 10 is absolute minimum otherwise the unittests fail
        self.threadpool=set()
        self.workqueue=Queue.Queue()
        for _ in range(numthreads):
            worker=SocketWorker(self, callbackObject)
            self.threadpool.add(worker)
            worker.start()
        log.info("%d worker threads started", len(self.threadpool))
    def __del__(self):
        if hasattr(self,"sock") and self.sock is not None:
            self.sock.close()
            self.sock=None
    def requestLoop(self, loopCondition=lambda:True, others=None):
        log.debug("threadpool server requestloop")
        while (self.sock is not None) and loopCondition():
            try:
                ins=[self.sock]
                if others:
                    ins.extend(others[0])
                    ins,_,_=selectfunction(ins,[],[],1)
                    if not ins:
                        continue
                if self.sock in ins:
                    ins.remove(self.sock)
                    csock, caddr=self.sock.accept()
                    log.debug("connection from %s",caddr)
                    self.workqueue.put((csock,caddr))
                if ins:
                    try:
                        others[1](ins)  # handle events from other sockets
                    except socket.error,x:
                        log.warn("there was an uncaught socket error for the other sockets: %s",x)
            except socket.timeout:
                pass  # just continue the loop on a timeout on accept
            except socket.error:
                if not loopCondition():
                    # swallow the socket error if loop terminates anyway
                    # this can occur if we are asked to shutdown, socket can be invalid then
                    break
                else:
                    raise
        log.debug("threadpool server exits requestloop")
    def close(self, joinWorkers=False): 
        log.debug("closing threadpool server")
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except Exception:
                pass
            self.sock=None
        for worker in list(self.threadpool):
            worker.running=False
            self.workqueue.put((None,None)) # put a 'stop' sentinel in the worker queue
        if joinWorkers:
            for worker in list(self.threadpool):
                worker.join()
    def fileno(self):
        return self.sock.fileno()
                
    def pingConnection(self):
        """bit of a hack to trigger a blocking server to get out of the loop, useful at clean shutdowns"""
        try:
            sock=createSocket(connect=self._socketaddr)
            sock.send("!!!!!!!!!!!!!!!!!!!!!")
            sock.close()
        except socket.error:
            pass

