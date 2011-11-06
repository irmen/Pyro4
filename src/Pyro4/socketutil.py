"""
Low level socket utilities.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import socket, os, errno, time, sys
from Pyro4.errors import ConnectionClosedError, TimeoutError

import select
if os.name=="java":
    selectfunction = select.cpython_compatible_select
else:
    selectfunction = select.select

# Note: other interesting errnos are EPERM, ENOBUFS, EMFILE
# but it seems to me that all these signify an unrecoverable situation.
# So I didn't include them in de list of retryable errors.
ERRNO_RETRIES=[errno.EINTR, errno.EAGAIN, errno.EWOULDBLOCK, errno.EINPROGRESS]
if hasattr(errno, "WSAEINTR"):
    ERRNO_RETRIES.append(errno.WSAEINTR)
if hasattr(errno, "WSAEWOULDBLOCK"):
    ERRNO_RETRIES.append(errno.WSAEWOULDBLOCK)
if hasattr(errno, "WSAEINPROGRESS"):
    ERRNO_RETRIES.append(errno.WSAEINPROGRESS)

ERRNO_BADF=[errno.EBADF]
if hasattr(errno, "WSAEBADF"):
    ERRNO_BADF.append(errno.WSAEBADF)

ERRNO_ENOTSOCK=[errno.ENOTSOCK]
if hasattr(errno, "WSAENOTSOCK"):
    ERRNO_ENOTSOCK.append(errno.WSAENOTSOCK)

ERRNO_EADDRNOTAVAIL=[errno.EADDRNOTAVAIL]
if hasattr(errno, "WSAEADDRNOTAVAIL"):
    ERRNO_EADDRNOTAVAIL.append(errno.WSAEADDRNOTAVAIL)

ERRNO_EADDRINUSE=[errno.EADDRINUSE]
if hasattr(errno, "WSAEADDRINUSE"):
    ERRNO_EADDRINUSE.append(errno.WSAEADDRINUSE)


def getIpAddress(hostname=None):
    """returns the IP address for the current, or another, hostname"""
    return socket.gethostbyname(hostname or socket.gethostname())


def getMyIpAddress(hostname=None, workaround127=False):
    """returns our own IP address. If you enable the workaround,
    it will use a little hack if the system reports our own ip address
    as being localhost (this is often the case on Linux)"""
    ip=getIpAddress(hostname)
    if workaround127 and (ip.startswith("127.") or ip=="0.0.0.0"):
        ip=getInterfaceAddress("4.2.2.2")   # 'abuse' a level 3 DNS server
    return ip


def getInterfaceAddress(peer_ip_address):
    """tries to find the ip address of the interface that connects to a given host"""
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((peer_ip_address, 53))   # 53=dns
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


if sys.version_info<(3, 0):
    EMPTY_BYTES=""
else:
    EMPTY_BYTES=bytes([])


def receiveData(sock, size):
    """Retrieve a given number of bytes from a socket.
    It is expected the socket is able to supply that number of bytes.
    If it isn't, an exception is raised (you will not get a zero length result
    or a result that is smaller than what you asked for). The partial data that
    has been received however is stored in the 'partialData' attribute of
    the exception object."""
    try:
        retrydelay=0.0
        msglen=0
        chunks=[]
        if hasattr(socket, "MSG_WAITALL"):
            # waitall is very convenient and if a socket error occurs,
            # we can assume the receive has failed. No need for a loop,
            # unless it is a retryable error.
            # Some systems have an erratic MSG_WAITALL and sometimes still return
            # less bytes than asked. In that case, we drop down into the normal
            # receive loop to finish the task.
            while True:
                try:
                    data=sock.recv(size, socket.MSG_WAITALL)
                    if len(data)==size:
                        return data
                    # less data than asked, drop down into normal receive loop to finish
                    msglen=len(data)
                    chunks=[data]
                    break
                except socket.timeout:
                    raise TimeoutError("receiving: timeout")
                except socket.error:
                    x=sys.exc_info()[1]
                    err=getattr(x, "errno", x.args[0])
                    if err not in ERRNO_RETRIES:
                        raise ConnectionClosedError("receiving: connection lost: "+str(x))
                    time.sleep(0.00001+retrydelay)  # a slight delay to wait before retrying
                    retrydelay=__nextRetrydelay(retrydelay)
        # old fashioned recv loop, we gather chunks until the message is complete
        while True:
            try:
                while msglen<size:
                    # 60k buffer limit avoids problems on certain OSes like VMS, Windows
                    chunk=sock.recv(min(60000, size-msglen))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    msglen+=len(chunk)
                data=EMPTY_BYTES.join(chunks)
                del chunks
                if len(data)!=size:
                    err=ConnectionClosedError("receiving: not enough data")
                    err.partialData=data  # store the message that was received until now
                    raise err
                return data  # yay, complete
            except socket.timeout:
                raise TimeoutError("receiving: timeout")
            except socket.error:
                x=sys.exc_info()[1]
                err=getattr(x, "errno", x.args[0])
                if err not in ERRNO_RETRIES:
                    raise ConnectionClosedError("receiving: connection lost: "+str(x))
                time.sleep(0.00001+retrydelay)  # a slight delay to wait before retrying
                retrydelay=__nextRetrydelay(retrydelay)
    except socket.timeout:
        raise TimeoutError("receiving: timeout")


def sendData(sock, data):
    """
    Send some data over a socket.
    Some systems have problems with ``sendall()`` when the socket is in non-blocking mode.
    For instance, Mac OS X seems to be happy to throw EAGAIN errors too often.
    This function falls back to using a regular send loop if needed.
    """
    if sock.gettimeout() is None:
        # socket is in blocking mode, we can use sendall normally.
        while True:
            try:
                sock.sendall(data)
                return
            except socket.timeout:
                raise TimeoutError("sending: timeout")
            except socket.error:
                x=sys.exc_info()[1]
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
            except socket.error:
                x=sys.exc_info()[1]
                err=getattr(x, "errno", x.args[0])
                if err not in ERRNO_RETRIES:
                    raise ConnectionClosedError("sending: connection lost: "+str(x))
                time.sleep(0.00001+retrydelay)  # a slight delay to wait before retrying
                retrydelay=__nextRetrydelay(retrydelay)


_GLOBAL_DEFAULT_TIMEOUT=object()

def createSocket(bind=None, connect=None, reuseaddr=False, keepalive=True, timeout=_GLOBAL_DEFAULT_TIMEOUT, noinherit=False):
    """
    Create a socket. Default socket options are keepalives.
    If 'bind' or 'connect' is a string, it is assumed a Unix domain socket is requested.
    Otherwise, a normal tcp/ip socket is used.
    """
    if bind and connect:
        raise ValueError("bind and connect cannot both be specified at the same time")
    family=socket.AF_INET
    if type(bind) is str or type(connect) is str:
        family=socket.AF_UNIX
    sock=socket.socket(family, socket.SOCK_STREAM)
    if reuseaddr:
        setReuseAddr(sock)
    if noinherit:
        setNoInherit(sock)
    if timeout==0:
        timeout = None
    if timeout is not _GLOBAL_DEFAULT_TIMEOUT:
        sock.settimeout(timeout)
    if bind:
        if type(bind) is tuple and bind[1]==0:
            bindOnUnusedPort(sock, bind[0])
        else:
            sock.bind(bind)
        try:
            sock.listen(100)
        except Exception:
            pass  # jython sometimes raises errors here
    if connect:
        try:
            sock.connect(connect)
        except socket.error:
            # This can happen when the socket is in non-blocking mode (or has a timeout configured).
            # We check if it is a retryable errno (usually EINPROGRESS).
            # If so, we use select() to wait until the socket is in writable state,
            # essentially rebuilding a blocking connect() call.
            xv = sys.exc_info()[1]
            errno = xv.errno
            if errno in ERRNO_RETRIES:
                if timeout is _GLOBAL_DEFAULT_TIMEOUT:
                    timeout = None
                timeout = max(0.1, timeout)   # avoid polling behavior with timeout=0
                while True:
                    sr, sw, se = selectfunction([], [sock], [sock], timeout)
                    if sock in sw:
                        break   # yay, writable now, connect() completed
                    elif sock in se:
                        raise socket.error("connect failed")
            else:
                raise
    if keepalive:
        setKeepalive(sock)
    return sock


def createBroadcastSocket(bind=None, reuseaddr=False, timeout=_GLOBAL_DEFAULT_TIMEOUT):
    """Create a udp broadcast socket."""
    sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    if reuseaddr:
        setReuseAddr(sock)
    if timeout is None:
        sock.settimeout(None)
    else:
        if timeout is not _GLOBAL_DEFAULT_TIMEOUT and (not bind or os.name!="java"):
            # only set timeout on the udp socket in this case, because Jython
            # has a problem with timeouts on udp sockets, see http://bugs.jython.org/issue1018
            sock.settimeout(timeout)
    if bind:
        host,port=bind
        host=host or ""
        if port==0:
            bindOnUnusedPort(sock, host)
        else:
            sock.bind((host,port))
    return sock


def setReuseAddr(sock):
    """sets the SO_REUSEADDR option on the socket, if possible."""
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except Exception:
        pass


def setKeepalive(sock):
    """sets the SO_KEEPALIVE option on the socket, if possible."""
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    except Exception:
        pass

try:
    import fcntl

    def setNoInherit(sock):
        """Mark the given socket fd as non-inheritable to child processes"""
        fd = sock.fileno()
        flags = fcntl.fcntl(fd, fcntl.F_GETFD)
        fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)

except ImportError:
    # no fcntl available, try the windows version
    try:
        from ctypes import windll, WinError

        def setNoInherit(sock):
            """Mark the given socket fd as non-inheritable to child processes"""
            if not windll.kernel32.SetHandleInformation(sock.fileno(), 1, 0):
                raise WinError()

    except ImportError:
        # nothing available, define a dummy function
        def setNoInherit(sock):
            """Mark the given socket fd as non-inheritable to child processes (dummy)"""
            pass


class SocketConnection(object):
    """A wrapper class for plain sockets, containing various methods such as :meth:`send` and :meth:`recv`"""
    __slots__=["sock", "objectId"]

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
    timeout=property(getTimeout, setTimeout)


def findProbablyUnusedPort(family=socket.AF_INET, socktype=socket.SOCK_STREAM):
    """Returns an unused port that should be suitable for binding (likely, but not guaranteed).
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
