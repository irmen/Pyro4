"""
Socket server based on socket multiplexing. Doesn't use threads.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong.
irmen@razorvine.net - http://www.razorvine.net/python/Pyro
"""

import socket, select, sys, logging
from Pyro4 import socketutil, errors
import Pyro4

log=logging.getLogger("Pyro.socketserver.multiplexed")


class MultiplexedSocketServerBase(object):
    """base class for multiplexed transport server for socket connections"""
    def init(self, daemon, host, port):
        log.info("starting multiplexed socketserver")
        self.sock=None
        self.sock=socketutil.createSocket(bind=(host, port), timeout=Pyro4.config.COMMTIMEOUT, noinherit=True)
        self.clients=[]
        self.daemon=daemon
        sockaddr=self.sock.getsockname()
        if sockaddr[0].startswith("127."):
            if host is None or host.lower()!="localhost" and not host.startswith("127."):
                log.warn("weird DNS setup: %s resolves to localhost (127.x.x.x)", host)
        host=host or sockaddr[0]
        port=port or sockaddr[1]
        self.locationStr="%s:%d" % (host, port)

    def __del__(self):
        if self.sock is not None:
            self.sock.close()
            self.sock=None

    def events(self, eventsockets):
        """used for external event loops: handle events that occur on one of the sockets of this server"""
        for s in eventsockets:
            if s is self.sock:
                # server socket, means new connection
                conn=self._handleConnection(self.sock)
                if conn:
                    self.clients.append(conn)
            else:
                # must be client socket, means remote call
                try:
                    self.daemon.handleRequest(s)
                except (socket.error, errors.ConnectionClosedError):
                    # client went away.
                    s.close()
                    if s in self.clients:
                        self.clients.remove(s)

    def _handleConnection(self, sock):
        try:
            csock, caddr=sock.accept()
            log.debug("connection from %s", caddr)
            if Pyro4.config.COMMTIMEOUT:
                csock.settimeout(Pyro4.config.COMMTIMEOUT)
        except socket.error:
            x=sys.exc_info()[1]
            err=getattr(x, "errno", x.args[0])
            if err in socketutil.ERRNO_RETRIES:
                # just ignore this error for now and continue
                log.warn("accept() failed errno=%d, shouldn't happen", err)
                return None
            if err in socketutil.ERRNO_BADF:
                # our server socket got destroyed
                raise errors.ConnectionClosedError("server socket closed")
            raise
        try:
            conn=socketutil.SocketConnection(csock)
            if self.daemon.handshake(conn):
                return conn
        except (socket.error, errors.PyroError):
            x=sys.exc_info()[1]
            log.warn("error during connect: %s", x)
            csock.close()
        return None

    def close(self):
        log.debug("closing socketserver")
        if self.sock:
            self.sock.close()
        self.sock=None
        for c in self.clients:
            try:
                c.close()
            except Exception:
                pass
        self.clients=[]

    @property
    def sockets(self):
        socks=[self.sock]
        socks.extend(self.clients)
        return socks

    def wakeup(self):
        """bit of a hack to trigger a blocking server to get out of the loop, useful at clean shutdowns"""
        try:
            if sys.version_info<(3, 0):
                self.sock.send("!"*16)
            else:
                self.sock.send(bytes([1]*16))
        except socket.error:
            pass


class SocketServer_Poll(MultiplexedSocketServerBase):
    """transport server for socket connections, poll loop multiplex version."""

    def loop(self, loopCondition=lambda: True):
        log.debug("enter poll-based requestloop")
        poll=select.poll()
        try:
            fileno2connection={}  # map fd to original connection object
            poll.register(self.sock.fileno(), select.POLLIN | select.POLLPRI)
            fileno2connection[self.sock.fileno()]=self.sock
            while loopCondition():
                polls=poll.poll(1000*Pyro4.config.POLLTIMEOUT)
                for (fd, mask) in polls:
                    conn=fileno2connection[fd]
                    if conn is self.sock:
                        try:
                            conn=self._handleConnection(self.sock)
                        except errors.ConnectionClosedError:
                            log.info("server socket was closed, stopping requestloop")
                            return
                        if conn:
                            poll.register(conn.fileno(), select.POLLIN | select.POLLPRI)
                            fileno2connection[conn.fileno()]=conn
                    else:
                        try:
                            self.daemon.handleRequest(conn)
                        except (socket.error, errors.ConnectionClosedError):
                            # client went away.
                            try:
                                fn=conn.fileno()
                            except socket.error:
                                pass
                            else:
                                poll.unregister(fn)
                                del fileno2connection[fn]
                                conn.close()
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
                rlist=self.clients[:]
                rlist.append(self.sock)
                try:
                    rlist, _, _=select.select(rlist, [], [], Pyro4.config.POLLTIMEOUT)
                except select.error:
                    if loopCondition():
                        raise
                    else:
                        # swallow the select error if the loopcondition is no longer true, and exit loop
                        # this can occur if we are shutting down and the socket is no longer valid
                        break
                if self.sock in rlist:
                    rlist.remove(self.sock)
                    try:
                        conn=self._handleConnection(self.sock)
                        if conn:
                            self.clients.append(conn)
                    except errors.ConnectionClosedError:
                        log.info("server socket was closed, stopping requestloop")
                        return
                for conn in rlist[:]:
                    if conn in self.clients:
                        rlist.remove(conn)
                        try:
                            self.daemon.handleRequest(conn)
                        except (socket.error, errors.ConnectionClosedError):
                            # client went away.
                            conn.close()
                            if conn in self.clients:
                                self.clients.remove(conn)
            except socket.timeout:
                pass   # just continue the loop on a timeout
            except KeyboardInterrupt:
                log.debug("stopping on break signal")
                break
        log.debug("exit select-based requestloop")
