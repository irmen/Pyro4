"""
Socket server based on a worker thread pool. Doesn't use select.

Uses a single worker thread per client connection.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement, print_function
import socket
import logging
import sys
import os
import struct
import Pyro4.util
from Pyro4 import socketutil, errors
from .threadpool import Pool, NoFreeWorkersError
from ..threadutil import Lock

log = logging.getLogger("Pyro4.threadpoolserver")
_client_disconnect_lock = Lock()


class ClientConnectionJob(object):
    """
    Takes care of a single client connection and all requests
    that may arrive during its life span.
    """

    def __init__(self, clientSocket, clientAddr, daemon):
        self.csock = socketutil.SocketConnection(clientSocket)
        self.caddr = clientAddr
        self.daemon = daemon

    def __call__(self):
        if self.handleConnection():
            try:
                while True:
                    try:
                        self.daemon.handleRequest(self.csock)
                    except (socket.error, errors.ConnectionClosedError):
                        # client went away.
                        log.debug("disconnected %s", self.caddr)
                        break
                    except errors.SecurityError:
                        log.debug("security error on client %s", self.caddr)
                        break
                    except errors.TimeoutError as x:
                        # for timeout errors we're not really interested in detailed traceback info
                        log.warning("error during handleRequest: %s" % x)
                        break
                    except:
                        # other errors log a warning, break this loop and close the client connection
                        ex_t, ex_v, ex_tb = sys.exc_info()
                        tb = Pyro4.util.formatTraceback(ex_t, ex_v, ex_tb)
                        msg = "error during handleRequest: %s; %s" % (ex_v, "".join(tb))
                        log.warning(msg)
                        break
            finally:
                with _client_disconnect_lock:
                    try:
                        self.daemon.clientDisconnect(self.csock)
                    except Exception as x:
                        log.warning("Error in clientDisconnect: " + str(x))
                self.csock.close()

    def handleConnection(self):
        # connection handshake
        try:
            if self.daemon._handshake(self.csock):
                return True
            self.csock.close()
        except:
            ex_t, ex_v, ex_tb = sys.exc_info()
            tb = Pyro4.util.formatTraceback(ex_t, ex_v, ex_tb)
            log.warning("error during connect/handshake: %s; %s", ex_v, "\n".join(tb))
            self.csock.close()
        return False

    def interrupt(self):
        """attempt to interrupt the worker's request loop"""
        try:
            self.csock.sock.shutdown(socket.SHUT_RDWR)
            self.csock.sock.setblocking(False)
        except (OSError, socket.error):
            pass
        if hasattr(socket, "SO_RCVTIMEO"):
            # setting a recv timeout seems to break the blocking call to recv() on some systems
            try:
                self.csock.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, struct.pack("ii", 1, 1))
            except socket.error:
                pass
        self.csock.close()

    def denyConnection(self, reason):
        log.warn("client connection was denied: "+reason)
        # return failed handshake
        self.daemon._handshake(self.csock, denied_reason=reason)
        self.csock.close()


class SocketServer_Threadpool(object):
    """transport server for socket connections, worker thread pool version."""

    def __init__(self):
        self.daemon = self.sock = self._socketaddr = self.locationStr = self.pool = None

    def init(self, daemon, host, port, unixsocket=None):
        log.info("starting thread pool socketserver")
        self.daemon = daemon
        self.sock = None
        bind_location = unixsocket if unixsocket else (host, port)
        self.sock = socketutil.createSocket(bind=bind_location, reuseaddr=Pyro4.config.SOCK_REUSE, timeout=Pyro4.config.COMMTIMEOUT, noinherit=True, nodelay=Pyro4.config.SOCK_NODELAY)
        self._socketaddr = self.sock.getsockname()
        if not unixsocket and self._socketaddr[0].startswith("127."):
            if host is None or host.lower() != "localhost" and not host.startswith("127."):
                log.warning("weird DNS setup: %s resolves to localhost (127.x.x.x)", host)
        if unixsocket:
            self.locationStr = "./u:" + unixsocket
        else:
            host = host or self._socketaddr[0]
            port = port or self._socketaddr[1]
            if ":" in host:  # ipv6
                self.locationStr = "[%s]:%d" % (host, port)
            else:
                self.locationStr = "%s:%d" % (host, port)
        self.pool = Pool()

    def __del__(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None
        if self.pool is not None:
            self.pool.close()
            self.pool = None

    def __repr__(self):
        return "<%s on %s, %d workers, %d waiting jobs>" % (self.__class__.__name__, self.locationStr,
                                                    self.pool.num_workers(), self.pool.waiting_jobs())

    def loop(self, loopCondition=lambda: True):
        log.debug("threadpool server requestloop")
        while (self.sock is not None) and loopCondition():
            try:
                self.events([self.sock])
            except socket.error:
                x = sys.exc_info()[1]
                err = getattr(x, "errno", x.args[0])
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

    def combine_loop(self, server):
        raise TypeError("You can't use the loop combiner on the threadpool server type")

    def events(self, eventsockets):
        """used for external event loops: handle events that occur on one of the sockets of this server"""
        # we only react on events on our own server socket.
        # all other (client) sockets are owned by their individual threads.
        assert self.sock in eventsockets
        try:
            csock, caddr = self.sock.accept()
            log.debug("connected %s", caddr)
            if Pyro4.config.COMMTIMEOUT:
                csock.settimeout(Pyro4.config.COMMTIMEOUT)
            job = ClientConnectionJob(csock, caddr, self.daemon)
            try:
                self.pool.process(job)
            except NoFreeWorkersError:
                job.denyConnection("no free workers, increase server threadpool size")
        except socket.timeout:
            pass  # just continue the loop on a timeout on accept

    def close(self):
        log.debug("closing threadpool server")
        if self.sock:
            sockname = None
            try:
                sockname = self.sock.getsockname()
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
            self.sock = None
        self.pool.close()

    @property
    def sockets(self):
        # the server socket is all we care about, all client sockets are running in their own threads
        return [self.sock]

    @property
    def selector(self):
        raise TypeError("threadpool server doesn't have multiplexing selector")

    def wakeup(self):
        interruptSocket(self._socketaddr)


def interruptSocket(address):
    """bit of a hack to trigger a blocking server to get out of the loop, useful at clean shutdowns"""
    try:
        sock = socketutil.createSocket(connect=address, keepalive=False, timeout=None)
        socketutil.triggerSocket(sock)
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except (OSError, socket.error):
            pass
        sock.close()
    except socket.error:
        pass
