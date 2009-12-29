"""Pyro socket utilities."""

import socket
import errno
import logging
import select
import os
from Pyro.errors import ConnectionClosedError, TimeoutError, PyroError

ERRNO_RETRIES=[errno.EINTR, errno.EAGAIN, errno.EWOULDBLOCK]
if hasattr(errno, "WSAEINTR"): ERRNO_RETRIES.append(errno.WSAEINTR)
if hasattr(errno, "WSAEWOULDBLOCK"): ERRNO_RETRIES.append(errno.WSAEWOULDBLOCK)

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

def setReuseAddr(sock):
    """sets the SO_REUSEADDR option on the socket.""" 
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,
            sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR) | 1)
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


class SocketServer(object):
    """transport server for socket connections"""
    def __init__(self, callbackObject, host, port):
        self.sock=createSocket(bind=(host,port))
        self.clients=[]
        self.callback=callbackObject
        if not host:
            host=self.sock.getsockname()[0]
        self.locationStr="%s:%d" % (host,port)
    def __del__(self):
        if hasattr(self,"sock") and self.sock is not None:
            self.sock.close()
            self.sock=None
    if hasattr(select,"poll"):
        log.info("using poll loop")
        def requestLoop(self, loopCondition=lambda:True):
            try:
                poll=select.poll()
                fileno2connection={}  # map fd to original connection object
                if os.name=="java":
                    self.sock.setblocking(False) # jython/java requirement
                poll.register(self.sock.fileno(), select.POLLIN | select.POLLPRI)
                fileno2connection[self.sock.fileno()]=self.sock
                while loopCondition():
                    polls=poll.poll(1000)
                    for (fd,mask) in polls:
                        conn=fileno2connection[fd]
                        if conn is self.sock:
                            conn=self.handleConnection(self.sock)
                            if conn:
                                if os.name=="java":
                                    conn.sock.setblocking(False)
                                poll.register(conn.fileno(), select.POLLIN | select.POLLPRI)
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
        log.info("using select loop")
        _selectfunction=select.select
        if os.name=="java":
            # Jython needs a select wrapper. Usually it will use the poll loop above though. 
        	from select import cpython_compatible_select as _selectfunction
        def requestLoop(self, loopCondition=lambda:True):
            while loopCondition():
                rlist=self.clients[:]
                rlist.append(self.sock)
                rlist,wlist,xlist=self._selectfunction(rlist, [], [], 1)
                if self.sock in rlist:
                    rlist.remove(self.sock)
                    conn=self.handleConnection(self.sock)
                    self.clients.append(conn)
                for conn in rlist:
                    try:
                        self.callback.handleRequest(conn)
                    except (socket.error,ConnectionClosedError),x:
                        # client went away.
                        conn.close()
                        self.clients.remove(conn)

    def handleConnection(self, sock):
        try:
            csock, caddr=sock.accept()
        except socket.error,x:
            err=getattr(x,"errno",x.args[0])
            print "ACCEPT FAILED ERRNO",err
            if err in ERRNO_RETRIES:
                # just ignore this error
                return None
        log.debug("new connection from %s",caddr)
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
            c.close()
        self.callback=None
