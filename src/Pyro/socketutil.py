"""Pyro socket utilities."""

import socket
import errno
from Pyro.errors import ConnectionClosedError, TimeoutError


def getHostname(full=False, ip=None):
    """obtain the hostname or fully qualified name of the current, or another, machine""" 
    if full or ip:
        return socket.getfqdn(ip or "")
    else:
        return socket.gethostname()

def getIpAddress(hostname=None):
    """returns the IP address for the current, or another, hostname"""
    return socket.gethostbyname(hostname or getHostname())

def receiveData(sock, size):
    """Retrieve a given number of bytes from a socket.
    It is expected the socket is able to supply that number of bytes.
    If it isn't, an exception is raised (you will not get a zero length result
    or a result that is smaller than what you asked for). The partial data that
    has been received however is stored in the 'partialMsg' attribute of
    the exception object."""

    def receive(sock,size):
        """use optimal receive call to get the data"""
        if hasattr(socket,"MSG_WAITALL"):
            data=sock.recv(size, socket.MSG_WAITALL)
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
            err.partialMsg=data  # store the message that was received until now
            raise err
        return data
    
    while True:
        try:
            return receive(sock,size)
        except socket.timeout:
            raise TimeoutError("receiving: timeout")
        except socket.error,x:
            if x.args[0] == errno.EINTR or (hasattr(errno, "WSAEINTR") and x.args[0] == errno.WSAEINTR):
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
        pass

def setKeepalive(sock):
    """sets the SO_KEEPALIVE option on the socket."""
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    except:
        pass
