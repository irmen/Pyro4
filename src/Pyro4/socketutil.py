"""
Low level socket utilities.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import socket
import errno
import time
import sys
import select
import Pyro4.constants
from Pyro4.errors import CommunicationError, TimeoutError, ConnectionClosedError

try:
    InterruptedError()  # new since Python 3.4
except NameError:
    class InterruptedError(Exception):
        pass


# Note: other interesting errnos are EPERM, ENOBUFS, EMFILE
# but it seems to me that all these signify an unrecoverable situation.
# So I didn't include them in the list of retryable errors.
ERRNO_RETRIES = [errno.EINTR, errno.EAGAIN, errno.EWOULDBLOCK, errno.EINPROGRESS]
if hasattr(errno, "WSAEINTR"):
    ERRNO_RETRIES.append(errno.WSAEINTR)
if hasattr(errno, "WSAEWOULDBLOCK"):
    ERRNO_RETRIES.append(errno.WSAEWOULDBLOCK)
if hasattr(errno, "WSAEINPROGRESS"):
    ERRNO_RETRIES.append(errno.WSAEINPROGRESS)

ERRNO_BADF = [errno.EBADF]
if hasattr(errno, "WSAEBADF"):
    ERRNO_BADF.append(errno.WSAEBADF)

ERRNO_ENOTSOCK = [errno.ENOTSOCK]
if hasattr(errno, "WSAENOTSOCK"):
    ERRNO_ENOTSOCK.append(errno.WSAENOTSOCK)
if not hasattr(socket, "SOL_TCP"):
    socket.SOL_TCP = socket.IPPROTO_TCP

ERRNO_EADDRNOTAVAIL = [errno.EADDRNOTAVAIL]
if hasattr(errno, "WSAEADDRNOTAVAIL"):
    ERRNO_EADDRNOTAVAIL.append(errno.WSAEADDRNOTAVAIL)

ERRNO_EADDRINUSE = [errno.EADDRINUSE]
if hasattr(errno, "WSAEADDRINUSE"):
    ERRNO_EADDRINUSE.append(errno.WSAEADDRINUSE)

if sys.version_info >= (3, 0):
    basestring = str


def getIpVersion(hostnameOrAddress):
    """
    Determine what the IP version is of the given hostname or ip address (4 or 6).
    First, it resolves the hostname or address to get an IP address.
    Then, if the resolved IP contains a ':' it is considered to be an ipv6 address,
    and if it contains a '.', it is ipv4.
    """
    address = getIpAddress(hostnameOrAddress)
    if "." in address:
        return 4
    elif ":" in address:
        return 6
    else:
        raise CommunicationError("Unknown IP address format" + address)


def getIpAddress(hostname, workaround127=False, ipVersion=None):
    """
    Returns the IP address for the given host. If you enable the workaround,
    it will use a little hack if the ip address is found to be the loopback address.
    The hack tries to discover an externally visible ip address instead (this only works for ipv4 addresses).
    Set ipVersion=6 to return ipv6 addresses, 4 to return ipv4, 0 to let OS choose the best one or None to use Pyro4.config.PREFER_IP_VERSION.
    """

    def getaddr(ipVersion):
        if ipVersion == 6:
            family = socket.AF_INET6
        elif ipVersion == 4:
            family = socket.AF_INET
        elif ipVersion == 0:
            family = socket.AF_UNSPEC
        else:
            raise ValueError("unknown value for argument ipVersion.")
        ip = socket.getaddrinfo(hostname or socket.gethostname(), 80, family, socket.SOCK_STREAM, socket.SOL_TCP)[0][4][0]
        if workaround127 and (ip.startswith("127.") or ip == "0.0.0.0"):
            ip = getInterfaceAddress("4.2.2.2")
        return ip

    try:
        if hostname and ':' in hostname and ipVersion is None:
            ipVersion = 0
        return getaddr(Pyro4.config.PREFER_IP_VERSION) if ipVersion is None else getaddr(ipVersion)
    except socket.gaierror:
        if ipVersion == 6 or (ipVersion is None and Pyro4.config.PREFER_IP_VERSION == 6):
            raise socket.error("unable to determine IPV6 address")
        return getaddr(0)


def getInterfaceAddress(ip_address):
    """tries to find the ip address of the interface that connects to the given host's address"""
    family = socket.AF_INET if getIpVersion(ip_address) == 4 else socket.AF_INET6
    sock = socket.socket(family, socket.SOCK_DGRAM)
    try:
        sock.connect((ip_address, 53))  # 53=dns
        return sock.getsockname()[0]
    finally:
        sock.close()


def __nextRetrydelay(delay):
    # first try a few very short delays,
    # if that doesn't work, increase by 0.1 sec every time
    if delay == 0.0:
        return 0.001
    if delay == 0.001:
        return 0.01
    return delay + 0.1


def receiveData(sock, size):
    """Retrieve a given number of bytes from a socket.
    It is expected the socket is able to supply that number of bytes.
    If it isn't, an exception is raised (you will not get a zero length result
    or a result that is smaller than what you asked for). The partial data that
    has been received however is stored in the 'partialData' attribute of
    the exception object."""
    try:
        retrydelay = 0.0
        msglen = 0
        chunks = []
        if Pyro4.config.USE_MSG_WAITALL:
            # waitall is very convenient and if a socket error occurs,
            # we can assume the receive has failed. No need for a loop,
            # unless it is a retryable error.
            # Some systems have an erratic MSG_WAITALL and sometimes still return
            # less bytes than asked. In that case, we drop down into the normal
            # receive loop to finish the task.
            while True:
                try:
                    data = sock.recv(size, socket.MSG_WAITALL)
                    if len(data) == size:
                        return data
                    # less data than asked, drop down into normal receive loop to finish
                    msglen = len(data)
                    chunks = [data]
                    break
                except socket.timeout:
                    raise TimeoutError("receiving: timeout")
                except socket.error:
                    x = sys.exc_info()[1]
                    err = getattr(x, "errno", x.args[0])
                    if err not in ERRNO_RETRIES:
                        raise ConnectionClosedError("receiving: connection lost: " + str(x))
                    time.sleep(0.00001 + retrydelay)  # a slight delay to wait before retrying
                    retrydelay = __nextRetrydelay(retrydelay)
        # old fashioned recv loop, we gather chunks until the message is complete
        while True:
            try:
                while msglen < size:
                    # 60k buffer limit avoids problems on certain OSes like VMS, Windows
                    chunk = sock.recv(min(60000, size - msglen))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    msglen += len(chunk)
                data = b"".join(chunks)
                del chunks
                if len(data) != size:
                    err = ConnectionClosedError("receiving: not enough data")
                    err.partialData = data  # store the message that was received until now
                    raise err
                return data  # yay, complete
            except socket.timeout:
                raise TimeoutError("receiving: timeout")
            except socket.error:
                x = sys.exc_info()[1]
                err = getattr(x, "errno", x.args[0])
                if err not in ERRNO_RETRIES:
                    raise ConnectionClosedError("receiving: connection lost: " + str(x))
                time.sleep(0.00001 + retrydelay)  # a slight delay to wait before retrying
                retrydelay = __nextRetrydelay(retrydelay)
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
        try:
            sock.sendall(data)
            return
        except socket.timeout:
            raise TimeoutError("sending: timeout")
        except socket.error:
            x = sys.exc_info()[1]
            raise ConnectionClosedError("sending: connection lost: " + str(x))
    else:
        # Socket is in non-blocking mode, use regular send loop.
        retrydelay = 0.0
        while data:
            try:
                sent = sock.send(data)
                data = data[sent:]
            except socket.timeout:
                raise TimeoutError("sending: timeout")
            except socket.error:
                x = sys.exc_info()[1]
                err = getattr(x, "errno", x.args[0])
                if err not in ERRNO_RETRIES:
                    raise ConnectionClosedError("sending: connection lost: " + str(x))
                time.sleep(0.00001 + retrydelay)  # a slight delay to wait before retrying
                retrydelay = __nextRetrydelay(retrydelay)


_GLOBAL_DEFAULT_TIMEOUT = object()


def createSocket(bind=None, connect=None, reuseaddr=False, keepalive=True, timeout=_GLOBAL_DEFAULT_TIMEOUT, noinherit=False, ipv6=False, nodelay=True):
    """
    Create a socket. Default socket options are keepalive and IPv4 family, and nodelay (nagle disabled).
    If 'bind' or 'connect' is a string, it is assumed a Unix domain socket is requested.
    Otherwise, a normal tcp/ip socket is used.
    Set ipv6=True to create an IPv6 socket rather than IPv4.
    Set ipv6=None to use the PREFER_IP_VERSION config setting.
    """
    if bind and connect:
        raise ValueError("bind and connect cannot both be specified at the same time")
    forceIPv6 = ipv6 or (ipv6 is None and Pyro4.config.PREFER_IP_VERSION == 6)
    if isinstance(bind, basestring) or isinstance(connect, basestring):
        family = socket.AF_UNIX
    elif not bind and not connect:
        family = socket.AF_INET6 if forceIPv6 else socket.AF_INET
    elif type(bind) is tuple:
        if not bind[0]:
            family = socket.AF_INET6 if forceIPv6 else socket.AF_INET
        else:
            if getIpVersion(bind[0]) == 4:
                if forceIPv6:
                    raise ValueError("IPv4 address is used bind argument with forceIPv6 argument:" + bind[0] + ".")
                family = socket.AF_INET
            elif getIpVersion(bind[0]) == 6:
                family = socket.AF_INET6
                # replace bind addresses by their ipv6 counterparts (4-tuple)
                bind = (bind[0], bind[1], 0, 0)
            else:
                raise ValueError("unknown bind format.")
    elif type(connect) is tuple:
        if not connect[0]:
            family = socket.AF_INET6 if forceIPv6 else socket.AF_INET
        else:
            if getIpVersion(connect[0]) == 4:
                if forceIPv6:
                    raise ValueError("IPv4 address is used in connect argument with forceIPv6 argument:" + bind[0] + ".")
                family = socket.AF_INET
            elif getIpVersion(connect[0]) == 6:
                family = socket.AF_INET6
                # replace connect addresses by their ipv6 counterparts (4-tuple)
                connect = (connect[0], connect[1], 0, 0)
            else:
                raise ValueError("unknown connect format.")
    else:
        raise ValueError("unknown bind or connect format.")
    sock = socket.socket(family, socket.SOCK_STREAM)
    if nodelay:
        setNoDelay(sock)
    if reuseaddr:
        setReuseAddr(sock)
    if noinherit:
        setNoInherit(sock)
    if timeout == 0:
        timeout = None
    if timeout is not _GLOBAL_DEFAULT_TIMEOUT:
        sock.settimeout(timeout)
    if bind:
        if type(bind) is tuple and bind[1] == 0:
            bindOnUnusedPort(sock, bind[0])
        else:
            sock.bind(bind)
        try:
            sock.listen(100)
        except Exception:
            pass
    if connect:
        try:
            sock.connect(connect)
        except socket.error:
            # This can happen when the socket is in non-blocking mode (or has a timeout configured).
            # We check if it is a retryable errno (usually EINPROGRESS).
            # If so, we use select() to wait until the socket is in writable state,
            # essentially rebuilding a blocking connect() call.
            xv = sys.exc_info()[1]
            errno = getattr(xv, "errno", 0)
            if errno in ERRNO_RETRIES:
                if timeout is _GLOBAL_DEFAULT_TIMEOUT or timeout < 0.1:
                    timeout = 0.1
                while True:
                    try:
                        sr, sw, se = select.select([], [sock], [sock], timeout)
                    except InterruptedError:
                        continue
                    if sock in sw:
                        break  # yay, writable now, connect() completed
                    elif sock in se:
                        raise socket.error("connect failed")
            else:
                raise
    if keepalive:
        setKeepalive(sock)
    return sock


def createBroadcastSocket(bind=None, reuseaddr=False, timeout=_GLOBAL_DEFAULT_TIMEOUT, ipv6=False):
    """
    Create a udp broadcast socket.
    Set ipv6=True to create an IPv6 socket rather than IPv4.
    Set ipv6=None to use the PREFER_IP_VERSION config setting.
    """
    forceIPv6 = ipv6 or (ipv6 is None and Pyro4.config.PREFER_IP_VERSION == 6)
    if not bind:
        family = socket.AF_INET6 if forceIPv6 else socket.AF_INET
    elif type(bind) is tuple:
        if not bind[0]:
            family = socket.AF_INET6 if forceIPv6 else socket.AF_INET
        else:
            if getIpVersion(bind[0]) == 4:
                if forceIPv6:
                    raise ValueError("IPv4 address is used with forceIPv6 option:" + bind[0] + ".")
                family = socket.AF_INET
            elif getIpVersion(bind[0]) == 6:
                family = socket.AF_INET6
                bind = (bind[0], bind[1], 0, 0)
            else:
                raise ValueError("unknown bind format: %r" % (bind,))
    else:
        raise ValueError("unknown bind format: %r" % (bind,))
    sock = socket.socket(family, socket.SOCK_DGRAM)
    if family == socket.AF_INET:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    if reuseaddr:
        setReuseAddr(sock)
    if timeout is None:
        sock.settimeout(None)
    else:
        if timeout is not _GLOBAL_DEFAULT_TIMEOUT:
            sock.settimeout(timeout)
    if bind:
        host = bind[0] or ""
        port = bind[1]
        if port == 0:
            bindOnUnusedPort(sock, host)
        else:
            if len(bind) == 2:
                sock.bind((host, port))  # ipv4
            elif len(bind) == 4:
                sock.bind((host, port, 0, 0))  # ipv6
            else:
                raise ValueError("bind must be None, 2-tuple or 4-tuple")
    return sock


def setReuseAddr(sock):
    """sets the SO_REUSEADDR option on the socket, if possible."""
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except Exception:
        pass


def setNoDelay(sock):
    """sets the TCP_NODELAY option on the socket (to disable Nagle's algorithm), if possible."""
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
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
        if sys.platform == "cli":
            raise NotImplementedError("IronPython can't obtain a proper HANDLE from a socket")
        from ctypes import windll, WinError, wintypes
        # help ctypes to set the proper args for this kernel32 call on 64-bit pythons
        _SetHandleInformation = windll.kernel32.SetHandleInformation
        _SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
        _SetHandleInformation.restype = wintypes.BOOL  # don't need this, but might as well

        def setNoInherit(sock):
            """Mark the given socket fd as non-inheritable to child processes"""
            if not _SetHandleInformation(sock.fileno(), 1, 0):
                raise WinError()

    except (ImportError, NotImplementedError):
        # nothing available, define a dummy function
        def setNoInherit(sock):
            """Mark the given socket fd as non-inheritable to child processes (dummy)"""
            pass


class SocketConnection(object):
    """A wrapper class for plain sockets, containing various methods such as :meth:`send` and :meth:`recv`"""
    __slots__ = ["sock", "objectId", "pyroInstances"]

    def __init__(self, sock, objectId=None):
        self.sock = sock
        self.objectId = objectId
        self.pyroInstances = {}    # pyro objects for instance_mode=session

    def __del__(self):
        self.close()

    def send(self, data):
        sendData(self.sock, data)

    def recv(self, size):
        return receiveData(self.sock, size)

    def close(self):
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except (OSError, socket.error):
            pass
        try:
            self.sock.close()
        except AttributeError:
            pass
        self.pyroInstances = {}   # force releasing the session instances

    def fileno(self):
        return self.sock.fileno()

    def setTimeout(self, timeout):
        self.sock.settimeout(timeout)

    def getTimeout(self):
        return self.sock.gettimeout()

    timeout = property(getTimeout, setTimeout)


def findProbablyUnusedPort(family=socket.AF_INET, socktype=socket.SOCK_STREAM):
    """Returns an unused port that should be suitable for binding (likely, but not guaranteed).
    This code is copied from the stdlib's test.test_support module."""
    tempsock = socket.socket(family, socktype)
    port = bindOnUnusedPort(tempsock)
    tempsock.close()
    del tempsock
    if sys.platform == "cli":
        return port + 1  # the actual port is somehow still in use by the socket when using IronPython
    return port


def bindOnUnusedPort(sock, host='localhost'):
    """Bind the socket to a free port and return the port number.
    This code is based on the code in the stdlib's test.test_support module."""
    if sock.family in (socket.AF_INET, socket.AF_INET6) and sock.type == socket.SOCK_STREAM:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            except socket.error:
                pass
    if sock.family == socket.AF_INET:
        if host == 'localhost':
            sock.bind(('127.0.0.1', 0))
        else:
            sock.bind((host, 0))
    elif sock.family == socket.AF_INET6:
        if host == 'localhost':
            sock.bind(('::1', 0, 0, 0))
        else:
            sock.bind((host, 0, 0, 0))
    else:
        raise CommunicationError("unsupported socket family: " + sock.family)
    return sock.getsockname()[1]


def triggerSocket(sock):
    """send a small data packet over the socket, to trigger it"""
    try:
        sock.sendall(b"!" * 16)
    except (socket.error, AttributeError):
        pass
