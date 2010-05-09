######################################################################
#
#  socket server based on select/poll. Doesn't use threads.
#
#  Pyro - Python Remote Objects.  Copyright by Irmen de Jong.
#  irmen@razorvine.net - http://www.razorvine.net/python/Pyro
#
######################################################################

import select, os, socket
import logging
from Pyro.socketutil import SocketConnection, createSocket, sendData, ERRNO_RETRIES, ERRNO_BADF
from Pyro.errors import ConnectionClosedError, PyroError

log=logging.getLogger("Pyro.socketserver.select")

class SocketServer(object):
    """transport server for socket connections, select/poll loop multiplex version."""
    def __init__(self, callbackObject, host, port, timeout=None):
        log.info("starting select/poll socketserver")
        self.sock=createSocket(bind=(host,port), timeout=timeout)
        self.clients=[]
        self.callback=callbackObject
        sockaddr=self.sock.getsockname()
        if sockaddr[0].startswith("127."):
            if host is None or host.lower()!="localhost" and not host.startswith("127."):
                log.warn("weird DNS setup: %s resolves to localhost (127.x.x.x)",host)
        host=host or sockaddr[0]
        port=port or sockaddr[1]
        self.locationStr="%s:%d" % (host,port)
    def __del__(self):
        if hasattr(self,"sock") and self.sock is not None:
            self.sock.close()
            self.sock=None
    if hasattr(select,"poll"):
        def requestLoop(self, loopCondition=lambda:True, others=None):
            log.debug("enter poll-based requestloop")
            try:
                poll=select.poll() #@UndefinedVariable (pydev)
                fileno2connection={}  # map fd to original connection object
                if os.name=="java":
                    self.sock.setblocking(False) # jython/java requirement
                poll.register(self.sock.fileno(), select.POLLIN | select.POLLPRI) #@UndefinedVariable (pydev)
                fileno2connection[self.sock.fileno()]=self.sock
                if others:
                    for sock in others[0]:
                        if os.name=="java":
                            sock.setblocking(False) # jython/java requirement
                        poll.register(sock.fileno(), select.POLLIN | select.POLLPRI) #@UndefinedVariable (pydev)
                        fileno2connection[sock.fileno()]=sock
                while loopCondition():
                    polls=poll.poll(2000)
                    for (fd,mask) in polls:
                        conn=fileno2connection[fd]
                        if conn is self.sock:
                            try:
                                conn=self.handleConnection(self.sock)
                            except ConnectionClosedError:
                                log.info("server socket was closed, stopping requestloop")
                                return
                            if conn:
                                if os.name=="java":
                                    conn.sock.setblocking(False) # jython/java requirement
                                poll.register(conn.fileno(), select.POLLIN | select.POLLPRI) #@UndefinedVariable (pydev)
                                fileno2connection[conn.fileno()]=conn
                        else:
                            if others and conn in others[0]:
                                try:
                                    others[1]([conn])  # handle events from other socket
                                except socket.error,x:
                                    log.warn("there was an uncaught socket error for the other sockets: %s",x)
                            else:
                                try:
                                    self.callback.handleRequest(conn)
                                except (socket.error,ConnectionClosedError):
                                    # client went away.
                                    poll.unregister(conn.fileno())
                                    del fileno2connection[conn.fileno()]
                                    conn.close()
            finally:
                if hasattr(poll, "close"):
                    poll.close()
            log.debug("exit poll-based requestloop")

    else:
        if os.name=="java":
            # Jython needs a select wrapper.
            selectfunction=select.cpython_compatible_select
        else:
            selectfunction=select.select
        def requestLoop(self, loopCondition=lambda:True, others=None):
            log.debug("entering select-based requestloop")
            while loopCondition():
                try:
                    rlist=self.clients[:]
                    rlist.append(self.sock)
                    if others:
                        rlist.extend(others[0])
                    rlist,_,_=selectfunction(rlist, [], [], 1)
                    if self.sock in rlist:
                        rlist.remove(self.sock)
                        try:
                            conn=self.handleConnection(self.sock)
                            if conn:
                                self.clients.append(conn)
                        except ConnectionClosedError:
                            log.info("server socket was closed, stopping requestloop")
                            return
                    for conn in rlist[:]:
                        if conn in self.clients:
                            rlist.remove(conn)
                            try:
                                if self.callback:
                                    self.callback.handleRequest(conn)
                            except (socket.error,ConnectionClosedError):
                                # client went away.
                                conn.close()
                                if conn in self.clients:
                                    self.clients.remove(conn)
                    if rlist:
                        try:
                            others[1](rlist)  # handle events from other sockets
                        except socket.error,x:
                            log.warn("there was an uncaught socket error for the other sockets: %s",x)
                except socket.timeout:
                    pass   # just continue the loop on a timeout
            log.debug("exit select-based requestloop")

    def handleConnection(self, sock):
        try:
            csock, caddr=sock.accept()
            log.debug("connection from %s",caddr)
        except socket.error,x:
            err=getattr(x,"errno",x.args[0])
            if err in ERRNO_RETRIES:
                # just ignore this error for now
                print "ACCEPT FAILED ERRNO=",err  # XXX Jython issue
                log.warn("accept() failed errno=%d, shouldn't happen", err) # XXX this will spam the log...
                return None
            if err in ERRNO_BADF:
                # our server socket got destroyed
                raise ConnectionClosedError("server socket closed")
            raise
        try:
            conn=SocketConnection(csock)
            if self.callback.handshake(conn):
                return conn
        except (socket.error, PyroError), x:
            log.warn("error during connect: %s",x)
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
        self.callback=None

    def pingConnection(self):
        """bit of a hack to trigger a blocking server to get out of the loop, useful at clean shutdowns"""
        try:
            sendData(self.sock, "!!!!!!!!!!!!!!!!!!!!")
        except Exception:
            pass
