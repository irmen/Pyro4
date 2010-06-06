"""
Low level socket utilities.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong.
irmen@razorvine.net - http://www.razorvine.net/python/Pyro
"""

import socket, os, errno, logging, time
from Pyro.errors import ConnectionClosedError,TimeoutError,CommunicationError

# Note: other interesting errnos are EPERM, ENOBUFS, EMFILE
# but it seems to me that all these signify an unrecoverable situation.
# So I didn't include them in de list of retryable errors.
ERRNO_RETRIES=[errno.EINTR, errno.EAGAIN, errno.EWOULDBLOCK]
if hasattr(errno, "WSAEINTR"):
    ERRNO_RETRIES.append(errno.WSAEINTR)
if hasattr(errno, "WSAEWOULDBLOCK"):
    ERRNO_RETRIES.append(errno.WSAEWOULDBLOCK)

ERRNO_BADF=[errno.EBADF]
if hasattr(errno, "WSAEBADF"):
    ERRNO_BADF.append(errno.WSAEBADF)

log=logging.getLogger("Pyro.socketutil")

def getIpAddress(hostname=None):
    """returns the IP address for the current, or another, hostname"""
    return socket.gethostbyname(hostname or socket.gethostname())

def getMyIpAddress(hostname=None, workaround127=False):
    """returns our own IP address. If you enable the workaround,
    it will use a little hack if the system reports our own ip address
    as being localhost (this is often the case on Linux)"""
    ip=getIpAddress(hostname)
    if ip.startswith("127.") and workaround127:
        s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("4.2.2.2",53))   # 'abuse' a level 3 DNS server
        ip=s.getsockname()[0]
        s.close()
    return ip

def __nextRetrydelay(delay):
    # first try a few very short delays,
    # if that doesn't work, increase by 0.1 sec every time
    if delay==0.0:
        return 0.001
    if delay==0.001:
        return 0.01
    return delay+0.1

def receiveData(sock, size):
    """Retrieve a given number of bytes from a socket.
    It is expected the socket is able to supply that number of bytes.
    If it isn't, an exception is raised (you will not get a zero length result
    or a result that is smaller than what you asked for). The partial data that
    has been received however is stored in the 'partialData' attribute of
    the exception object."""
    try:
        retrydelay=0.0
        if hasattr(socket,"MSG_WAITALL"):
            # waitall is very convenient and if a socket error occurs,
            # we can assume the receive has failed. No need for a loop,
            # unless it is a retryable error.
            while True:
                try:
                    data=sock.recv(size, socket.MSG_WAITALL) #@UndefinedVariable (pydev)
                    if len(data)!=size:
                        raise ConnectionClosedError("receiving: not enough data")
                    return data
                except socket.timeout:
                    raise TimeoutError("receiving: timeout")
                except socket.error,x:
                    err=getattr(x,"errno",x.args[0])
                    if err not in ERRNO_RETRIES:
                        raise ConnectionClosedError("receiving: connection lost: "+str(x))
                    time.sleep(0.00001+retrydelay)  # a slight delay to wait before retrying
                    retrydelay=__nextRetrydelay(retrydelay)                
        # old fashioned recv loop, we gather chunks until the message is complete
        msglen=0
        chunks=[]
        while True:
            try:
                while msglen<size:
                    # 60k buffer limit avoids problems on certain OSes like VMS, Windows
                    chunk=sock.recv(min(60000,size-msglen))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    msglen+=len(chunk)
                data="".join(chunks)
                del chunks
                if len(data)!=size:
                    err=ConnectionClosedError("receiving: not enough data")
                    err.partialData=data  # store the message that was received until now
                    raise err
                return data  # yay, complete
            except socket.timeout:
                raise TimeoutError("receiving: timeout")
            except socket.error,x:
                err=getattr(x,"errno",x.args[0])
                if err not in ERRNO_RETRIES:
                    raise ConnectionClosedError("receiving: connection lost: "+str(x))
                time.sleep(0.00001+retrydelay)  # a slight delay to wait before retrying
                retrydelay=__nextRetrydelay(retrydelay)                
    except socket.timeout:
        raise TimeoutError("receiving: timeout")
    
            
def sendData(sock, data):
    """Send some data over a socket."""
    # Some OS-es have problems with sendall when the socket is in non-blocking mode.
    # For instance, Mac OS X seems to be happy to throw EAGAIN errors too often.
    # We fall back to using a regular send loop if needed.
    if sock.gettimeout() is None:
        # socket is in blocking mode, we can use sendall normally.
        while True:
            try:
                sock.sendall(data)
                return
            except socket.timeout:
                raise TimeoutError("sending: timeout")
            except socket.error,x:
                raise ConnectionClosedError("sending: connection lost: "+str(x))
    else:
        # Socket is in non-blocking mode, use regular send loop.
        retrydelay=0.0
        while data: 
            try: 
                sent = sock.send(data) 
                data = data[sent:]
            except socket.timeout:
                raise TimeoutError("sending: timeout")
            except socket.error, x:
                err=getattr(x,"errno",x.args[0])
                if err not in ERRNO_RETRIES:
                    raise ConnectionClosedError("sending: connection lost: "+str(x))
                time.sleep(0.00001+retrydelay)  # a slight delay to wait before retrying
                retrydelay=__nextRetrydelay(retrydelay)                


def createSocket(bind=None, connect=None, reuseaddr=True, keepalive=True, timeout=None):
    """Create a socket. Default options are keepalives and reuseaddr."""
    if timeout==0:
        timeout=None
    if bind and connect:
        raise ValueError("bind and connect cannot both be specified at the same time")
    sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if bind:
        if bind[1]==0:
            bindOnUnusedPort(sock, bind[0])
        else:
            sock.bind(bind)
        try:
            sock.listen(100)
        except Exception:
            pass  # jython sometimes raises errors here
    if connect:
        sock.connect(connect)
    if reuseaddr:
        setReuseAddr(sock)
    if keepalive:
        setKeepalive(sock)
    sock.settimeout(timeout)
    return sock

def createBroadcastSocket(bind=None, reuseaddr=True, timeout=None):
    """Create a udp broadcast socket."""
    if timeout==0:
        timeout=None
    sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    if reuseaddr:
        setReuseAddr(sock)
    if timeout is None:
        sock.settimeout(None)
    else:
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
                if bind[1]==0:
                    bindOnUnusedPort(sock, host)
                else:
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
    except Exception:
        log.info("cannot set SO_REUSEADDR")

def setKeepalive(sock):
    """sets the SO_KEEPALIVE option on the socket."""
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    except Exception:
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
        self.sock.close()
    def fileno(self):
        return self.sock.fileno()
    def setTimeout(self, timeout):
        self.sock.settimeout(timeout)
    def getTimeout(self):
        return self.sock.gettimeout()
    timeout=property(getTimeout,setTimeout)

def findUnusedPort(family=socket.AF_INET, socktype=socket.SOCK_STREAM):
    """Returns an unused port that should be suitable for binding. 
    This code is copied from the stdlib's test.test_support module."""
    tempsock = socket.socket(family, socktype)
    port = bindOnUnusedPort(tempsock)
    tempsock.close()
    del tempsock
    return port

def bindOnUnusedPort(sock, host='localhost'):
    """Bind the socket to a free port and return the port number. 
    This code is based on the code in the stdlib's test.test_support module."""
    if os.name!="java" and sock.family == socket.AF_INET and sock.type == socket.SOCK_STREAM:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    sock.bind((host, 0))
    if os.name=="java":
        try:
            sock.listen(100)  # otherwise jython always just returns 0 for the port
        except Exception:
            pass  # jython sometimes throws errors here
    port = sock.getsockname()[1]
    return port
