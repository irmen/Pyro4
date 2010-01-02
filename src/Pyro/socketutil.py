######################################################################
#
#  Low level socket utilities.
#
#  Pyro - Python Remote Objects.  Copyright by Irmen de Jong.
#  irmen@razorvine.net - http://www.razorvine.net/python/Pyro
#
######################################################################

import socket, select
import os, errno
import threading, Queue
import logging
from Pyro.errors import *

ERRNO_RETRIES=[errno.EINTR, errno.EAGAIN, errno.EWOULDBLOCK]
if hasattr(errno, "WSAEINTR"): ERRNO_RETRIES.append(errno.WSAEINTR)
if hasattr(errno, "WSAEWOULDBLOCK"): ERRNO_RETRIES.append(errno.WSAEWOULDBLOCK)

ERRNO_BADF=[errno.EBADF]
if hasattr(errno, "WSAEBADF"): ERRNO_BADF.append(errno.WSAEBADF)


log=logging.getLogger("Pyro.socketutil")

def getIpAddress(hostname=None):
    """returns the IP address for the current, or another, hostname"""
    return socket.gethostbyname(hostname or socket.gethostname())

def receiveData(sock, size):
    """Retrieve a given number of bytes from a socket.
    It is expected the socket is able to supply that number of bytes.
    If it isn't, an exception is raised (you will not get a zero length result
    or a result that is smaller than what you asked for). The partial data that
    has been received however is stored in the 'partialData' attribute of
    the exception object."""

    def receive(sock,size):
        """use optimal receive call to get the data"""
        if hasattr(socket,"MSG_WAITALL"):
            data=sock.recv(size, socket.MSG_WAITALL) #@UndefinedVariable (pydev)
        else:
            msglen=0
            msglist=[]
            while msglen<size:
                chunk=sock.recv(min(60000,size-msglen))  # 60k buffer limit avoids problems on certain OSes like VMS, Windows
                if not chunk:
                    break
                msglist.append(chunk)
                msglen+=len(chunk)
            data="".join(msglist)
        if len(data)!=size:
            err=ConnectionClosedError("receiving: not enough data")
            err.partialData=data  # store the message that was received until now
            raise err
        return data
    
    while True:
        try:
            return receive(sock,size)
        except socket.timeout:
            raise TimeoutError("receiving: timeout")
        except socket.error,x:
            err=getattr(x,"errno",x.args[0])
            if err in ERRNO_RETRIES:
                continue    # interrupted system call, just retry
            raise ConnectionClosedError("receiving: connection lost: "+str(x))

def sendData(sock, data):
    """Send some data over a socket."""
    try:
        sock.sendall(data)
    except socket.timeout:
        raise TimeoutError("sending: timeout")
    except socket.error,x:
        raise ConnectionClosedError("sending: connection lost: "+str(x))


def createSocket(bind=None, connect=None, reuseaddr=True, keepalive=True):
    """Create a socket. Default options are keepalives and reuseaddr."""
    if bind and connect:
        raise ValueError("bind and connect cannot both be specified at the same time")
    sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if bind:
        sock.bind(bind)
        sock.listen(200)   # rather arbitrary but not too large
    if connect:
        sock.connect(connect)
    if reuseaddr:
        setReuseAddr(sock)
    if keepalive:
        setKeepalive(sock)
    return sock

def createBroadcastSocket(bind=None, reuseaddr=True, timeout=None):
    """Create a udp broadcast socket."""
    sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    if reuseaddr:
        setReuseAddr(sock)
    if timeout is not None:
        if bind and os.name=="java":
            # Jython has a problem with timeouts on udp sockets, see http://bugs.jython.org/issue1018
            log.warn("not setting timeout on broadcast socket due to Jython issue 1018")
        else:
            sock.settimeout(timeout)
    if bind:
        if bind[0]:
            hosts=[bind[0]]
        else:
            hosts=["<broadcast>", "", "255.255.255.255"]
        for host in hosts:
            try:
                sock.bind((host, bind[1]))
                return sock
            except socket.error:
                continue
        sock.close()
        raise CommunicationError("cannot bind broadcast socket")
    return sock
    
def setReuseAddr(sock):
    """sets the SO_REUSEADDR option on the socket.""" 
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except:
        log.info("cannot set SO_REUSEADDR")

def setKeepalive(sock):
    """sets the SO_KEEPALIVE option on the socket."""
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    except:
        log.info("cannot set SO_KEEPALIVE")


class SocketConnection(object):
    """A connection wrapper for sockets"""
    __slots__=["sock","objectId"]
    def __init__(self, sock, objectId=None):
        self.sock=sock
        self.objectId=objectId
    def __del__(self):
        self.close()
    def send(self, data):
        sendData(self.sock, data)
    def recv(self, size):
        return receiveData(self.sock, size)
    def close(self):
        if hasattr(self,"sock") and self.sock is not None:
            self.sock.close()
        self.sock=None
    def fileno(self):
        return self.sock.fileno()


class SocketWorker(threading.Thread):
    """worker thread to process requests"""
    def __init__(self, workqueue, threadpool, callback):
        super(SocketWorker,self).__init__()
        self.setDaemon(True)
        self.queue=workqueue
        self.threadpool=threadpool
        self.callback=callback
    def run(self):
        self.running=True
        try:
            while self.running: # loop over all connections in the queue
                self.csock,self.caddr = self.queue.get()
                if self.csock is None and self.caddr is None:
                    # this was a 'stop' sentinel
                    self.running=False
                    break
                self.csock=SocketConnection(self.csock)
                if self.handleConnection(self.csock):
                    while self.running:   # loop over all requests during a single connection
                        try:
                            self.callback.handleRequest(self.csock)
                        except (socket.error,ConnectionClosedError),x:
                            # client went away.
                            self.csock.close()
                            break
        finally:
            self.threadpool.remove(self)
    def handleConnection(self,conn):
        try:
            if self.callback.handshake(conn):
                return True
        except (socket.error, PyroError), x:
            log.warn("error during connect: %s",x)
            conn.close()
        return False
                    
class SocketServer_Threadpool(object):
    """transport server for socket connections, worker thread pool version."""
    def __init__(self, callbackObject, host, port):
        log.info("starting thread pool socketserver")
        self.sock=createSocket(bind=(host,port))
        self._socketaddr=self.sock.getsockname()
        host=host or self._socketaddr[0]
        port=port or self._socketaddr[1]
        self.locationStr="%s:%d" % (host,port)
        numthreads=5    # XXX configurable
        self.threadpool=set()
        self.queue=Queue.Queue()
        for x in range(numthreads):
            worker=SocketWorker(self.queue, self.threadpool, callbackObject)
            self.threadpool.add(worker)
            worker.start()
        log.info("%d worker threads", len(self.threadpool))
    def __del__(self):
        if hasattr(self,"sock") and self.sock is not None:
            self.sock.close()
            self.sock=None
    def requestLoop(self, loopCondition=lambda:True):
        while (self.sock is not None) and loopCondition():
            csock, caddr=self.sock.accept()
            log.debug("new connection from %s",caddr)
            self.queue.put((csock,caddr))
    def close(self): 
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except Exception:
                pass
            self.sock=None
        for worker in list(self.threadpool):
            worker.running=False
            self.queue.put((None,None)) # put a 'stop' sentinel in the worker queue
                
    def pingConnection(self):
        """bit of a hack to trigger a blocking server to get out of the loop, useful at clean shutdowns"""
        try:
            sock=createSocket(connect=self._socketaddr)
            sendData(sock, "!!!!!!!!!!!!!!!!!!!!")
            sock.close()
        except Exception:
            pass


class SocketServer_Select(object):
    """transport server for socket connections, select/poll loop multiplex version."""
    def __init__(self, callbackObject, host, port):
        log.info("starting select/poll socketserver")
        self.sock=createSocket(bind=(host,port))
        self.clients=[]
        self.callback=callbackObject
        sockaddr=self.sock.getsockname()
        host=host or sockaddr[0]
        port=port or sockaddr[1]
        self.locationStr="%s:%d" % (host,port)
    def __del__(self):
        if hasattr(self,"sock") and self.sock is not None:
            self.sock.close()
            self.sock=None
    if hasattr(select,"poll"):
        def requestLoop(self, loopCondition=lambda:True):
            log.info("entering poll-based requestloop")
            try:
                poll=select.poll() #@UndefinedVariable (pydev)
                fileno2connection={}  # map fd to original connection object
                if os.name=="java":
                    self.sock.setblocking(False) # jython/java requirement
                poll.register(self.sock.fileno(), select.POLLIN | select.POLLPRI) #@UndefinedVariable (pydev)
                fileno2connection[self.sock.fileno()]=self.sock
                while loopCondition():
                    polls=poll.poll(1000)
                    for (fd,mask) in polls:
                        conn=fileno2connection[fd]
                        if conn is self.sock:
                            try:
                                conn=self.handleConnection(self.sock)
                            except ConnectionClosedError:
                                log.info("server socket was closed, stopping requestloop")
                                return
                            if conn:
                                if os.name=="java":
                                    conn.sock.setblocking(False) # jython/java requirement
                                poll.register(conn.fileno(), select.POLLIN | select.POLLPRI) #@UndefinedVariable (pydev)
                                fileno2connection[conn.fileno()]=conn
                        else:
                            try:
                                self.callback.handleRequest(conn)
                            except (socket.error,ConnectionClosedError),x:
                                # client went away.
                                poll.unregister(conn.fileno())
                                del fileno2connection[conn.fileno()]
                                conn.close()
            finally:
                if hasattr(poll, "close"):
                    poll.close()

    else:
        _selectfunction=select.select
        if os.name=="java":
            # Jython needs a select wrapper. Usually it will use the poll loop above though. 
            from select import cpython_compatible_select as _selectfunction   #@UnresolvedImport (pydev)
        def requestLoop(self, loopCondition=lambda:True):
            log.info("entering select-based requestloop")
            while loopCondition():
                rlist=self.clients[:]
                rlist.append(self.sock)
                rlist,wlist,xlist=self._selectfunction(rlist, [], [], 1)
                if self.sock in rlist:
                    rlist.remove(self.sock)
                    try:
                        conn=self.handleConnection(self.sock)
                        if conn:
                            self.clients.append(conn)
                    except ConnectionClosedError:
                        log.info("server socket was closed, stopping requestloop")
                        return
                for conn in rlist:
                    try:
                        if self.callback:
                            self.callback.handleRequest(conn)
                    except (socket.error,ConnectionClosedError),x:
                        # client went away.
                        conn.close()
                        if conn in self.clients:
                            self.clients.remove(conn)

    def handleConnection(self, sock):
        try:
            csock, caddr=sock.accept()
            log.debug("new connection from %s",caddr)
        except socket.error,x:
            err=getattr(x,"errno",x.args[0])
            if err in ERRNO_RETRIES:
                # just ignore this error for now
                print "ACCEPT FAILED ERRNO=",err  # XXX Jython issue
                return None
            if err in ERRNO_BADF:
                # our server socket got destroyed
                raise ConnectionClosedError("server socket closed")
            raise
        try:
            conn=SocketConnection(csock)
            if self.callback.handshake(conn):
                return conn
        except (socket.error, PyroError), x:
            log.warn("error during connect: %s",x)
            csock.close()
        return None

    def close(self): 
        if self.sock:
            self.sock.close()
        self.sock=None
        for c in self.clients:
            try:
                c.close()
            except:
                pass
        self.clients=[]
        self.callback=None

    def pingConnection(self):
        """bit of a hack to trigger a blocking server to get out of the loop, useful at clean shutdowns"""
        try:
            sendData(self.sock, "!!!!!!!!!!!!!!!!!!!!")
        except Exception:
            pass
    