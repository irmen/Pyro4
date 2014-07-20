"""
Socket server based on socket multiplexing. Doesn't use threads.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement, print_function
import socket
import select
import sys
import logging
import os
from Pyro4 import socketutil, errors, util
import Pyro4.constants

log = logging.getLogger("Pyro4.multiplexserver")


class MultiplexedSocketServerBase(object):
    """base class for multiplexed transport server for socket connections"""

    def __init__(self):
        self.sock = self.daemon = self.locationStr = None
        self.clients = set()

    def init(self, daemon, host, port, unixsocket=None):
        log.info("starting multiplexed socketserver")
        self.sock = None
        bind_location = unixsocket if unixsocket else (host, port)
        self.sock = socketutil.createSocket(bind=bind_location, reuseaddr=Pyro4.config.SOCK_REUSE, timeout=Pyro4.config.COMMTIMEOUT, noinherit=True)
        self.clients = set()
        self.daemon = daemon
        sockaddr = self.sock.getsockname()
        if not unixsocket and sockaddr[0].startswith("127."):
            if host is None or host.lower() != "localhost" and not host.startswith("127."):
                log.warning("weird DNS setup: %s resolves to localhost (127.x.x.x)", host)
        if unixsocket:
            self.locationStr = "./u:" + unixsocket
        else:
            host = host or sockaddr[0]
            port = port or sockaddr[1]
            if ":" in host:  # ipv6
                self.locationStr = "[%s]:%d" % (host, port)
            else:
                self.locationStr = "%s:%d" % (host, port)

    def __repr__(self):
        return "<%s on %s, %d connections>" % (self.__class__.__name__, self.locationStr, len(self.clients))

    def __del__(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def events(self, eventsockets):
        """used for external event loops: handle events that occur on one of the sockets of this server"""
        for s in eventsockets:
            if s is self.sock:
                # server socket, means new connection
                conn = self._handleConnection(self.sock)
                if conn:
                    self.clients.add(conn)
            else:
                # must be client socket, means remote call
                active = self.handleRequest(s)
                if not active:
                    s.close()
                    self.clients.discard(s)

    def _handleConnection(self, sock):
        try:
            if sock is None:
                return
            csock, caddr = sock.accept()
            if Pyro4.config.COMMTIMEOUT:
                csock.settimeout(Pyro4.config.COMMTIMEOUT)
        except socket.error:
            x = sys.exc_info()[1]
            err = getattr(x, "errno", x.args[0])
            if err in socketutil.ERRNO_RETRIES:
                # just ignore this error for now and continue
                log.warning("accept() failed errno=%d, shouldn't happen", err)
                return None
            if err in socketutil.ERRNO_BADF or err in socketutil.ERRNO_ENOTSOCK:
                # our server socket got destroyed
                raise errors.ConnectionClosedError("server socket closed")
            raise
        try:
            conn = socketutil.SocketConnection(csock)
            if self.daemon._handshake(conn):
                return conn
        except:  # catch all errors, otherwise the event loop could terminate
            ex_t, ex_v, ex_tb = sys.exc_info()
            tb = util.formatTraceback(ex_t, ex_v, ex_tb)
            log.warning("error during connect/handshake: %s; %s", ex_v, "\n".join(tb))
            try:
                csock.shutdown(socket.SHUT_RDWR)
            except (OSError, socket.error):
                pass
            csock.close()
        return None

    def close(self):
        log.debug("closing socketserver")
        if self.sock:
            sockname = None
            try:
                sockname = self.sock.getsockname()
            except socket.error:
                pass
            self.sock.close()
            if type(sockname) is str:
                # it was a Unix domain socket, remove it from the filesystem
                if os.path.exists(sockname):
                    os.remove(sockname)
        self.sock = None
        for c in self.clients:
            try:
                c.close()
            except Exception:
                pass
        self.clients = set()

    @property
    def sockets(self):
        socks = [self.sock]
        socks.extend(self.clients)
        return socks

    def wakeup(self):
        """bit of a hack to trigger a blocking server to get out of the loop, useful at clean shutdowns"""
        socketutil.triggerSocket(self.sock)

    def handleRequest(self, conn):
        """Handles a single connection request event and returns if the connection is still active"""
        try:
            self.daemon.handleRequest(conn)
            return True
        except (socket.error, errors.ConnectionClosedError, errors.SecurityError):
            # client went away or caused a security error.
            # close the connection silently.
            return False
        except:
            # other error occurred, close the connection, but also log a warning
            ex_t, ex_v, ex_tb = sys.exc_info()
            tb = util.formatTraceback(ex_t, ex_v, ex_tb)
            msg = "error during handleRequest: %s; %s" % (ex_v, "".join(tb))
            log.warning(msg)
            return False


class SocketServer_Poll(MultiplexedSocketServerBase):
    """transport server for socket connections, poll loop multiplex version."""

    def loop(self, loopCondition=lambda: True):
        log.debug("enter poll-based requestloop")
        poll = select.poll()
        try:
            fileno2connection = {}  # map fd to original connection object
            rlist = list(self.clients) + [self.sock]
            for r in rlist:
                poll.register(r.fileno(), select.POLLIN | select.POLLPRI)
                fileno2connection[r.fileno()] = r
            while loopCondition():
                polls = poll.poll(1000 * Pyro4.config.POLLTIMEOUT)
                for (fd, mask) in polls:
                    conn = fileno2connection[fd]
                    if conn is self.sock:
                        conn = self._handleConnection(self.sock)
                        if conn:
                            poll.register(conn.fileno(), select.POLLIN | select.POLLPRI)
                            fileno2connection[conn.fileno()] = conn
                            self.clients.add(conn)
                    else:
                        active = self.handleRequest(conn)
                        if not active:
                            try:
                                fn = conn.fileno()
                            except socket.error:
                                pass
                            else:
                                conn.close()
                                self.clients.discard(conn)
                                if fn in fileno2connection:
                                    poll.unregister(fn)
                                    del fileno2connection[fn]
        except KeyboardInterrupt:
            log.debug("stopping on break signal")
            pass
        finally:
            if hasattr(poll, "close"):
                poll.close()
        log.debug("exit poll-based requestloop")


class SocketServer_Select(MultiplexedSocketServerBase):
    """transport server for socket connections, select loop version."""

    def loop(self, loopCondition=lambda: True):
        log.debug("entering select-based requestloop")
        while loopCondition():
            try:
                rlist = list(self.clients)
                rlist.append(self.sock)
                try:
                    rlist, _, _ = socketutil.selectfunction(rlist, [], [], Pyro4.config.POLLTIMEOUT)
                except select.error:
                    if loopCondition():
                        raise
                    else:
                        # swallow the select error if the loopcondition is no longer true, and exit loop
                        # this can occur if we are shutting down and the socket is no longer valid
                        break
                if self.sock in rlist:
                    try:
                        rlist.remove(self.sock)
                    except ValueError:
                        pass  # this can occur when closing down, even when we just tested for presence in the list
                    conn = self._handleConnection(self.sock)
                    if conn:
                        self.clients.add(conn)
                for conn in rlist:
                    # no need to remove conn from rlist, because no more processing is done after this
                    if conn in self.clients:
                        active = self.handleRequest(conn)
                        if not active:
                            conn.close()
                            self.clients.discard(conn)
            except socket.timeout:
                pass  # just continue the loop on a timeout
            except KeyboardInterrupt:
                log.debug("stopping on break signal")
                break
        log.debug("exit select-based requestloop")
