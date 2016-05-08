"""
Socket server based on socket multiplexing. Doesn't use threads.
Uses the best available selector (kqueue, poll, select).

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement, print_function
import socket
import sys
import logging
import os
from collections import defaultdict
try:
    import selectors
except ImportError:
    import selectors34 as selectors
from Pyro4 import socketutil, errors, util
import Pyro4.constants

log = logging.getLogger("Pyro4.multiplexserver")


class SocketServer_Multiplex(object):
    """Multiplexed transport server for socket connections (uses select, poll, kqueue, ...)"""
    def __init__(self):
        self.sock = self.daemon = self.locationStr = None
        self.selector = selectors.DefaultSelector()

    def init(self, daemon, host, port, unixsocket=None):
        log.info("starting multiplexed socketserver")
        log.debug("selector implementation: "+self.selector.__class__.__name__)
        self.sock = None
        bind_location = unixsocket if unixsocket else (host, port)
        self.sock = socketutil.createSocket(bind=bind_location, reuseaddr=Pyro4.config.SOCK_REUSE, timeout=Pyro4.config.COMMTIMEOUT, noinherit=True, nodelay=Pyro4.config.SOCK_NODELAY)
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
        self.selector.register(self.sock, selectors.EVENT_READ, self)

    def __repr__(self):
        return "<%s on %s, %d connections>" % (self.__class__.__name__, self.locationStr, len(self.selector.get_map())-1)

    def __del__(self):
        if self.sock is not None:
            self.selector.close()
            self.sock.close()
            self.sock = None

    def events(self, eventsockets):
        """handle events that occur on one of the sockets of this server"""
        for s in eventsockets:
            if s is self.sock:
                # server socket, means new connection
                conn = self._handleConnection(self.sock)
                if conn:
                    self.selector.register(conn, selectors.EVENT_READ, self)
            else:
                # must be client socket, means remote call
                active = self.handleRequest(s)
                if not active:
                    try:
                        self.daemon.clientDisconnect(s)
                    except Exception as x:
                        log.warning("Error in clientDisconnect: " + str(x))
                    self.selector.unregister(s)
                    s.close()

    def _handleConnection(self, sock):
        try:
            if sock is None:
                return
            csock, caddr = sock.accept()
            log.debug("connected %s", caddr)
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
            conn.close()
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
        self.selector.close()
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

    @property
    def sockets(self):
        registrations = self.selector.get_map()
        if registrations:
            return [sk.fileobj for sk in registrations.values()]
        else:
            return []

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
            log.debug("disconnected %s", conn.sock.getpeername())
            return False
        except errors.TimeoutError as x:
            # for timeout errors we're not really interested in detailed traceback info
            log.warning("error during handleRequest: %s" % x)
            return False
        except:
            # other error occurred, close the connection, but also log a warning
            ex_t, ex_v, ex_tb = sys.exc_info()
            tb = util.formatTraceback(ex_t, ex_v, ex_tb)
            msg = "error during handleRequest: %s; %s" % (ex_v, "".join(tb))
            log.warning(msg)
            return False

    def loop(self, loopCondition=lambda: True):
        log.debug("entering multiplexed requestloop")
        while loopCondition():
            try:
                try:
                    events = self.selector.select(Pyro4.config.POLLTIMEOUT)
                except OSError:
                    events = []
                # get all the socket connection objects that have a READ event
                # (the WRITE events are ignored here, they're registered to let timeouts work etc)
                events_per_server = defaultdict(list)
                for key, mask in events:
                    if mask & selectors.EVENT_READ:
                        events_per_server[key.data].append(key.fileobj)
                for server, fileobjs in events_per_server.items():
                    server.events(fileobjs)
            except socket.timeout:
                pass  # just continue the loop on a timeout
            except KeyboardInterrupt:
                log.debug("stopping on break signal")
                break
        log.debug("exit select-based requestloop")

    def combine_loop(self, server):
        for sock in server.sockets:
            self.selector.register(sock, selectors.EVENT_READ, server)
        server.selector = self.selector
