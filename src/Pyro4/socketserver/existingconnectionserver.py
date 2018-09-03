"""
Socket server for a the special case of a single, already existing, connection.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import print_function
import socket
import sys
import logging
import ssl
from Pyro4 import socketutil, errors, util
from Pyro4.configuration import config


log = logging.getLogger("Pyro4.existingconnectionserver")


class SocketServer_ExistingConnection(object):
    def __init__(self):
        self.sock = self.daemon = self.locationStr = self.conn = None
        self.shutting_down = False

    def init(self, daemon, connected_socket):
        connected_socket.getpeername()   # check that it is connected
        if config.SSL and not isinstance(connected_socket, ssl.SSLSocket):
            raise socket.error("SSL configured for Pyro but existing socket is not a SSL socket")
        self.daemon = daemon
        self.sock = connected_socket
        log.info("starting server on user-supplied connected socket " + str(connected_socket))
        sn = connected_socket.getsockname()
        if hasattr(socket, "AF_UNIX") and connected_socket.family == socket.AF_UNIX:
            self.locationStr = "./u:" + (sn or "<<not-bound>>")
        else:
            host, port = sn[:2]
            if ":" in host:  # ipv6
                self.locationStr = "[%s]:%d" % (host, port)
            else:
                self.locationStr = "%s:%d" % (host, port)
        self.conn = socketutil.SocketConnection(connected_socket)

    def __repr__(self):
        return "<%s on %s>" % (self.__class__.__name__, self.locationStr)

    def __del__(self):
        if self.sock is not None:
            self.sock = None
            self.conn = None

    @property
    def selector(self):
        raise TypeError("single-connection server doesn't have multiplexing selector")

    @property
    def sockets(self):
        return [self.sock]

    def combine_loop(self, server):
        raise errors.PyroError("cannot combine servers when using user-supplied connected socket")

    def events(self, eventsockets):
        raise errors.PyroError("cannot combine events when using user-supplied connected socket")

    def shutdown(self):
        self.shutting_down = True
        self.close()
        self.sock = None
        self.conn = None

    def close(self):
        # don't close the socket itself, that's the user's responsibility
        self.sock = None
        self.conn = None

    def handleRequest(self):
        """Handles a single connection request event and returns if the connection is still active"""
        try:
            self.daemon.handleRequest(self.conn)
            return True
        except (socket.error, errors.ConnectionClosedError, errors.SecurityError) as x:
            # client went away or caused a security error.
            # close the connection silently.
            try:
                peername = self.conn.sock.getpeername()
                log.debug("disconnected %s", peername)
            except socket.error:
                log.debug("disconnected a client")
            self.shutdown()
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
        log.debug("entering requestloop")
        while loopCondition() and self.sock:
            try:
                self.handleRequest()
                self.daemon._housekeeping()
            except socket.timeout:
                pass  # just continue the loop on a timeout
            except KeyboardInterrupt:
                log.debug("stopping on break signal")
                break
