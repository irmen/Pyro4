"""
Core logic (uri, daemon, proxy stuff).

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import re, sys, time, os
import logging, uuid
from Pyro4 import constants, threadutil, util, socketutil, errors
from Pyro4.socketserver.threadpoolserver import SocketServer_Threadpool
from Pyro4.socketserver.multiplexserver import SocketServer_Select, SocketServer_Poll
from Pyro4 import futures
from Pyro4.message import Message
import Pyro4

__all__ = ["URI", "Proxy", "Daemon", "callback", "batch", "async"]

if sys.version_info >= (3, 0):
    basestring = str

log = logging.getLogger("Pyro4.core")


class URI(object):
    """
    Pyro object URI (universal resource identifier).
    The uri format is like this: ``PYRO:objectid@location`` where location is one of:

    - ``hostname:port`` (tcp/ip socket on given port)
    - ``./u:sockname`` (Unix domain socket on localhost)

    There is also a 'Magic format' for simple name resolution using Name server:
      ``PYRONAME:objectname[@location]``  (optional name server location, can also omit location port)

    You can write the protocol in lowercase if you like (``pyro:...``) but it will
    automatically be converted to uppercase internally.
    """
    uriRegEx = re.compile(r"(?P<protocol>[Pp][Yy][Rr][Oo][a-zA-Z]*):(?P<object>\S+?)(@(?P<location>\S+))?$")
    __slots__ = ("protocol", "object", "sockname", "host", "port", "object")

    def __init__(self, uri):
        if isinstance(uri, URI):
            state=uri.__getstate__()
            self.__setstate__(state)
            return
        if not isinstance(uri, basestring):
            raise TypeError("uri parameter object is of wrong type")
        self.sockname=self.host=self.port=None
        match=self.uriRegEx.match(uri)
        if not match:
            raise errors.PyroError("invalid uri")
        self.protocol=match.group("protocol").upper()
        self.object=match.group("object")
        location=match.group("location")
        if self.protocol=="PYRONAME":
            self._parseLocation(location, Pyro4.config.NS_PORT)
            return
        if self.protocol=="PYRO":
            if not location:
                raise errors.PyroError("invalid uri")
            self._parseLocation(location, None)
        else:
            raise errors.PyroError("invalid uri (protocol)")

    def _parseLocation(self, location, defaultPort):
        if not location:
            return
        if location.startswith("./u:"):
            self.sockname=location[4:]
            if (not self.sockname) or ':' in self.sockname:
                raise errors.PyroError("invalid uri (location)")
        else:
            if location.startswith("["):  # ipv6
                if location.startswith("[["):  # possible mistake: double-bracketing
                    raise errors.PyroError("invalid ipv6 address: enclosed in too many brackets")
                self.host, _, self.port = re.match(r"\[([0-9a-fA-F:%]+)](:(\d+))?", location).groups()
            else:
                self.host, _, self.port = location.partition(":")
            if not self.port:
                self.port=defaultPort
            try:
                self.port=int(self.port)
            except (ValueError, TypeError):
                raise errors.PyroError("invalid port in uri, port="+str(self.port))

    @staticmethod
    def isUnixsockLocation(location):
        """determine if a location string is for a Unix domain socket"""
        return location.startswith("./u:")

    @property
    def location(self):
        """property containing the location string, for instance ``"servername.you.com:5555"``"""
        if self.host:
            if ":" in self.host:    # ipv6
                return "[%s]:%d" % (self.host, self.port)
            else:
                return "%s:%d" % (self.host, self.port)
        elif self.sockname:
            return "./u:"+self.sockname
        else:
            return None

    def asString(self):
        """the string representation of this object"""
        result=self.protocol+":"+self.object
        location=self.location
        if location:
            result+="@"+location
        return result

    def __str__(self):
        string=self.asString()
        if sys.version_info<(3, 0) and type(string) is unicode:
            return string.encode("ascii", "replace")
        return string

    def __unicode__(self):
        return self.asString()

    def __repr__(self):
        return "<%s.%s at 0x%x, %s>" % (self.__class__.__module__, self.__class__.__name__, id(self), str(self))

    def __eq__(self, other):
        if not isinstance(other, URI):
            return False
        return (self.protocol, self.object, self.sockname, self.host, self.port) \
            == (other.protocol, other.object, other.sockname, other.host, other.port)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.protocol, self.object, self.sockname, self.host, self.port))

    # note: getstate/setstate are not needed if we use pickle protocol 2,
    # but this way it helps pickle to make the representation smaller by omitting all attribute names.

    def __getstate__(self):
        return self.protocol, self.object, self.sockname, self.host, self.port

    def __getstate_for_dict__(self):
        return self.__getstate__()

    def __setstate__(self, state):
        self.protocol, self.object, self.sockname, self.host, self.port = state


class _RemoteMethod(object):
    """method call abstraction"""
    def __init__(self, send, name):
        self.__send = send
        self.__name = name

    def __getattr__(self, name):
        return _RemoteMethod(self.__send, "%s.%s" % (self.__name, name))

    def __call__(self, *args, **kwargs):
        return self.__send(self.__name, args, kwargs)


def _check_hmac():
    if Pyro4.config.HMAC_KEY:
        if sys.version_info>=(3, 0) and type(Pyro4.config.HMAC_KEY) is not bytes:
            raise errors.PyroError("HMAC_KEY must be bytes type")


class Proxy(object):
    """
    Pyro proxy for a remote object. Intercepts method calls and dispatches them to the remote object.

    .. automethod:: _pyroBind
    .. automethod:: _pyroRelease
    .. automethod:: _pyroReconnect
    .. automethod:: _pyroBatch
    .. automethod:: _pyroAsync
    """
    __pyroAttributes=frozenset(["__getnewargs__", "__getinitargs__", "_pyroConnection", "_pyroUri", "_pyroOneway", "_pyroTimeout", "_pyroSeq"])

    def __init__(self, uri):
        """
        .. autoattribute:: _pyroOneway
        .. autoattribute:: _pyroTimeout
        """
        _check_hmac()  # check if hmac secret key is set
        if isinstance(uri, basestring):
            uri=URI(uri)
        elif not isinstance(uri, URI):
            raise TypeError("expected Pyro URI")
        self._pyroUri=uri
        self._pyroConnection=None
        self._pyroOneway=set()
        self._pyroSeq=0    # message sequence number
        self.__pyroTimeout=Pyro4.config.COMMTIMEOUT
        self.__pyroLock=threadutil.Lock()
        self.__pyroConnLock=threadutil.Lock()
        util.get_serializer(Pyro4.config.SERIALIZER)  # assert that the configured serializer is available
        if os.name=="java" and Pyro4.config.SERIALIZER=="marshal":
            import warnings
            warnings.warn("marshal doesn't work correctly with Jython (issue 2077); please choose another serializer", RuntimeWarning)

    def __del__(self):
        if hasattr(self, "_pyroConnection"):
            self._pyroRelease()

    def __getattr__(self, name):
        if name in Proxy.__pyroAttributes:
            # allows it to be safely pickled
            raise AttributeError(name)
        return _RemoteMethod(self._pyroInvoke, name)

    def __repr__(self):
        connected="connected" if self._pyroConnection else "not connected"
        return "<%s.%s at 0x%x, %s, for %s>" % (self.__class__.__module__, self.__class__.__name__,
               id(self), connected, self._pyroUri)

    def __unicode__(self):
        return str(self)

    def __getstate__(self):
        return self._pyroUri, self._pyroOneway, self.__pyroTimeout    # skip the connection

    def __getstate_for_dict__(self):
        return self._pyroUri.asString(), tuple(self._pyroOneway), self.__pyroTimeout

    def __setstate__(self, state):
        self._pyroUri, self._pyroOneway, self.__pyroTimeout = state
        self._pyroConnection=None
        self._pyroSeq=0
        self.__pyroLock=threadutil.Lock()
        self.__pyroConnLock=threadutil.Lock()

    def __copy__(self):
        uriCopy=URI(self._pyroUri)
        return Proxy(uriCopy)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._pyroRelease()

    def __eq__(self, other):
        if other is self:
            return True
        return isinstance(other, Proxy) and other._pyroUri == self._pyroUri and other._pyroOneway == self._pyroOneway

    def __ne__(self, other):
        if other and isinstance(other, Proxy):
            return other._pyroUri != self._pyroUri or other._pyroOneway != self._pyroOneway
        return True

    def __hash__(self):
        return hash(self._pyroUri) ^ hash(frozenset(self._pyroOneway))

    def _pyroRelease(self):
        """release the connection to the pyro daemon"""
        with self.__pyroConnLock:
            if self._pyroConnection is not None:
                self._pyroConnection.close()
                self._pyroConnection=None
                log.debug("connection released")

    def _pyroBind(self):
        """
        Bind this proxy to the exact object from the uri. That means that the proxy's uri
        will be updated with a direct PYRO uri, if it isn't one yet.
        If the proxy is already bound, it will not bind again.
        """
        return self.__pyroCreateConnection(True)

    def __pyroGetTimeout(self):
        return self.__pyroTimeout

    def __pyroSetTimeout(self, timeout):
        self.__pyroTimeout=timeout
        if self._pyroConnection is not None:
            self._pyroConnection.timeout=timeout
    _pyroTimeout=property(__pyroGetTimeout, __pyroSetTimeout)

    def _pyroInvoke(self, methodname, vargs, kwargs, flags=0):
        """perform the remote method call communication"""
        if self._pyroConnection is None:
            # rebind here, don't do it from inside the invoke because deadlock will occur
            self.__pyroCreateConnection()
        serializer = util.get_serializer(Pyro4.config.SERIALIZER)
        data, compressed = serializer.serializeCall(
            self._pyroConnection.objectId, methodname, vargs, kwargs,
            compress=Pyro4.config.COMPRESSION)
        if compressed:
            flags |= Pyro4.message.FLAGS_COMPRESSED
        if methodname in self._pyroOneway:
            flags |= Pyro4.message.FLAGS_ONEWAY
        with self.__pyroLock:
            self._pyroSeq=(self._pyroSeq+1)&0xffff
            if Pyro4.config.LOGWIRE:
                log.debug("proxy wiredata sending: msgtype=%d flags=0x%x ser=%d seq=%d data=%r" % (Pyro4.message.MSG_INVOKE, flags, serializer.serializer_id, self._pyroSeq, data))
            msg = Message(Pyro4.message.MSG_INVOKE, data, serializer.serializer_id, flags, self._pyroSeq)
            try:
                self._pyroConnection.send(msg.to_bytes())
                del msg  # invite GC to collect the object, don't wait for out-of-scope
                if flags & Pyro4.message.FLAGS_ONEWAY:
                    return None    # oneway call, no response data
                else:
                    msg = Message.recv(self._pyroConnection, [Pyro4.message.MSG_RESULT])
                    if Pyro4.config.LOGWIRE:
                        log.debug("proxy wiredata received: msgtype=%d flags=0x%x ser=%d seq=%d data=%r" % (msg.type, msg.flags, msg.serializer_id, msg.seq, msg.data) )
                    self.__pyroCheckSequence(msg.seq)
                    if msg.serializer_id != serializer.serializer_id:
                        error = "invalid serializer in response: %d" % msg.serializer_id
                        log.error(error)
                        raise errors.ProtocolError(error)
                    data = serializer.deserializeData(msg.data, compressed=msg.flags & Pyro4.message.FLAGS_COMPRESSED)
                    if msg.flags & Pyro4.message.FLAGS_EXCEPTION:
                        if sys.platform=="cli":
                            util.fixIronPythonExceptionForPickle(data, False)
                        raise data
                    else:
                        return data
            except (errors.CommunicationError, KeyboardInterrupt):
                # Communication error during read. To avoid corrupt transfers, we close the connection.
                # Otherwise we might receive the previous reply as a result of a new methodcall!
                # Special case for keyboardinterrupt: people pressing ^C to abort the client
                # may be catching the keyboardinterrupt in their code. We should probably be on the
                # safe side and release the proxy connection in this case too, because they might
                # be reusing the proxy object after catching the exception...
                self._pyroRelease()
                raise

    def __pyroCheckSequence(self, seq):
        if seq!=self._pyroSeq:
            err="invoke: reply sequence out of sync, got %d expected %d" % (seq, self._pyroSeq)
            log.error(err)
            raise errors.ProtocolError(err)

    def __pyroCreateConnection(self, replaceUri=False):
        """
        Connects this proxy to the remote Pyro daemon. Does connection handshake.
        Returns true if a new connection was made, false if an existing one was already present.
        """
        with self.__pyroConnLock:
            if self._pyroConnection is not None:
                return False     # already connected
            from Pyro4.naming import resolve  # don't import this globally because of cyclic dependancy
            uri=resolve(self._pyroUri)
            # socket connection (normal or Unix domain socket)
            conn=None
            log.debug("connecting to %s", uri)
            connect_location=uri.sockname if uri.sockname else (uri.host, uri.port)
            with self.__pyroLock:
                try:
                    if self._pyroConnection is not None:
                        return False    # already connected
                    sock=socketutil.createSocket(connect=connect_location, reuseaddr=Pyro4.config.SOCK_REUSE, timeout=self.__pyroTimeout)
                    conn=socketutil.SocketConnection(sock, uri.object)
                    # Do handshake. For now, no need to send anything. (message type CONNECT is not yet used)
                    msg = Message.recv(conn, None)
                    # any trailing data (dataLen>0) is an error message, if any
                except Exception:
                    x=sys.exc_info()[1]
                    if conn:
                        conn.close()
                    err="cannot connect: %s" % x
                    log.error(err)
                    if isinstance(x, errors.CommunicationError):
                        raise
                    else:
                        ce = errors.CommunicationError(err)
                        ce.__cause__ = x
                        raise ce
                else:
                    if msg.type==Pyro4.message.MSG_CONNECTFAIL:
                        error="connection rejected"
                        if msg.data:
                            data = msg.data
                            if sys.version_info>=(3, 0):
                                data=str(msg.data, "utf-8")
                            error+=", reason: " + data
                        conn.close()
                        log.error(error)
                        raise errors.CommunicationError(error)
                    elif msg.type==Pyro4.message.MSG_CONNECTOK:
                        self._pyroConnection=conn
                        if replaceUri:
                            self._pyroUri=uri
                        log.debug("connected to %s", self._pyroUri)
                        return True
                    else:
                        conn.close()
                        err="connect: invalid msg type %d received" % msg.type
                        log.error(err)
                        raise errors.ProtocolError(err)

    def _pyroReconnect(self, tries=100000000):
        """(re)connect the proxy to the daemon containing the pyro object which the proxy is for"""
        self._pyroRelease()
        while tries:
            try:
                self.__pyroCreateConnection()
                return
            except errors.CommunicationError:
                tries-=1
                if tries:
                    time.sleep(2)
        msg="failed to reconnect"
        log.error(msg)
        raise errors.ConnectionClosedError(msg)

    def _pyroBatch(self):
        """returns a helper class that lets you create batched method calls on the proxy"""
        return _BatchProxyAdapter(self)

    def _pyroAsync(self):
        """returns a helper class that lets you do asynchronous method calls on the proxy"""
        return _AsyncProxyAdapter(self)

    def _pyroInvokeBatch(self, calls, oneway=False):
        flags=Pyro4.message.FLAGS_BATCH
        if oneway:
            flags|=Pyro4.message.FLAGS_ONEWAY
        return self._pyroInvoke("<batch>", calls, None, flags)


class _BatchedRemoteMethod(object):
    """method call abstraction that is used with batched calls"""
    def __init__(self, calls, name):
        self.__calls = calls
        self.__name = name

    def __getattr__(self, name):
        return _BatchedRemoteMethod(self.__calls, "%s.%s" % (self.__name, name))

    def __call__(self, *args, **kwargs):
        self.__calls.append((self.__name, args, kwargs))


class _BatchProxyAdapter(object):
    """Helper class that lets you batch multiple method calls into one.
    It is constructed with a reference to the normal proxy that will
    carry out the batched calls. Call methods on this object thatyou want to batch,
    and finally call the batch proxy itself. That call will return a generator
    for the results of every method call in the batch (in sequence)."""
    def __init__(self, proxy):
        self.__proxy=proxy
        self.__calls=[]

    def __getattr__(self, name):
        return _BatchedRemoteMethod(self.__calls, name)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def __copy__(self):
        return self

    def __resultsgenerator(self, results):
        for result in results:
            if isinstance(result, futures._ExceptionWrapper):
                result.raiseIt()   # re-raise the remote exception locally.
            else:
                yield result   # it is a regular result object, yield that and continue.

    def __call__(self, oneway=False, async=False):
        if oneway and async:
            raise errors.PyroError("async oneway calls make no sense")
        if async:
            return _AsyncRemoteMethod(self, "<asyncbatch>")()
        else:
            results=self.__proxy._pyroInvokeBatch(self.__calls, oneway)
            self.__calls=[]   # clear for re-use
            if not oneway:
                return self.__resultsgenerator(results)

    def _pyroInvoke(self, name, args, kwargs):
        # ignore all parameters, we just need to execute the batch
        results=self.__proxy._pyroInvokeBatch(self.__calls)
        self.__calls=[]   # clear for re-use
        return self.__resultsgenerator(results)


class _AsyncProxyAdapter(object):
    def __init__(self, proxy):
        self.__proxy=proxy

    def __getattr__(self, name):
        return _AsyncRemoteMethod(self.__proxy, name)


class _AsyncRemoteMethod(object):
    """async method call abstraction (call will run in a background thread)"""
    def __init__(self, proxy, name):
        self.__proxy = proxy
        self.__name = name

    def __getattr__(self, name):
        return _AsyncRemoteMethod(self.__proxy, "%s.%s" % (self.__name, name))

    def __call__(self, *args, **kwargs):
        result=futures.FutureResult()
        thread=threadutil.Thread(target=self.__asynccall, args=(result, args, kwargs))
        thread.setDaemon(True)
        thread.start()
        return result

    def __asynccall(self, asyncresult, args, kwargs):
        try:
            # use a copy of the proxy otherwise calls would be serialized,
            # and use contextmanager to close the proxy after we're done
            with self.__proxy.__copy__() as proxy:
                value = proxy._pyroInvoke(self.__name, args, kwargs)
            asyncresult.value=value
        except Exception:
            # ignore any exceptions here, return them as part of the async result instead
            asyncresult.value=futures._ExceptionWrapper(sys.exc_info()[1])


def batch(proxy):
    """convenience method to get a batch proxy adapter"""
    return proxy._pyroBatch()


def async(proxy):
    """convenience method to get an async proxy adapter"""
    return proxy._pyroAsync()


def pyroObjectToAutoProxy(self):
    """reduce function that automatically replaces Pyro objects by a Proxy"""
    if Pyro4.config.AUTOPROXY:
        daemon = getattr(self, "_pyroDaemon", None)
        if daemon:
            # only return a proxy if the object is a registered pyro object
            return Pyro4.core.Proxy(daemon.uriFor(self))
    return self


class DaemonObject(object):
    """The part of the daemon that is exposed as a Pyro object."""
    def __init__(self, daemon):
        self.daemon=daemon

    def registered(self):
        """returns a list of all object names registered in this daemon"""
        return list(self.daemon.objectsById.keys())

    def ping(self):
        """a simple do-nothing method for testing purposes"""
        pass


class Daemon(object):
    """
    Pyro daemon. Contains server side logic and dispatches incoming remote method calls
    to the appropriate objects.
    """
    def __init__(self, host=None, port=0, unixsocket=None, nathost=None, natport=None):
        _check_hmac()  # check if hmac secret key is set
        if host is None:
            host=Pyro4.config.HOST
        if nathost is None:
            nathost=Pyro4.config.NATHOST
        if natport is None:
            natport=Pyro4.config.NATPORT or None
        if nathost and unixsocket:
            raise ValueError("cannot use nathost together with unixsocket")
        if (nathost is None) ^ (natport is None):
            raise ValueError("must provide natport with nathost")
        if Pyro4.config.SERVERTYPE=="thread":
            self.transportServer=SocketServer_Threadpool()
        elif Pyro4.config.SERVERTYPE=="multiplex":
            # choose the 'best' multiplexing implementation
            if os.name=="java":
                raise NotImplementedError("select or poll-based server is not supported for jython, use thread server instead")
            self.transportServer = SocketServer_Poll() if socketutil.hasPoll else SocketServer_Select()
        else:
            raise errors.PyroError("invalid server type '%s'" % Pyro4.config.SERVERTYPE)
        self.transportServer.init(self, host, port, unixsocket)
        #: The location (str of the form ``host:portnumber``) on which the Daemon is listening
        self.locationStr=self.transportServer.locationStr
        log.debug("created daemon on %s", self.locationStr)
        natport_for_loc = natport
        if natport==0:
            # expose internal port number as NAT port as well. (don't use port because it could be 0 and will be chosen by the OS)
            natport_for_loc = int(self.locationStr.split(":")[1])
        #: The NAT-location (str of the form ``nathost:natportnumber``) on which the Daemon is exposed for use with NAT-routing
        self.natLocationStr = "%s:%d" % (nathost, natport_for_loc) if nathost else None
        if self.natLocationStr:
            log.debug("NAT address is %s", self.natLocationStr)
        pyroObject=DaemonObject(self)
        pyroObject._pyroId=constants.DAEMON_NAME
        #: Dictionary from Pyro object id to the actual Pyro object registered by this id
        self.objectsById={pyroObject._pyroId: pyroObject}
        self.__mustshutdown=threadutil.Event()
        self.__loopstopped=threadutil.Event()
        self.__loopstopped.set()
        # assert that the configured serializers are available, and remember their ids:
        self.__serializer_ids = set([util.get_serializer(ser_name).serializer_id for ser_name in Pyro4.config.SERIALIZERS_ACCEPTED])
        log.debug("accepted serializers: %s" % Pyro4.config.SERIALIZERS_ACCEPTED)

    @property
    def sock(self):
        return self.transportServer.sock

    @property
    def sockets(self):
        return self.transportServer.sockets

    @staticmethod
    def serveSimple(objects, host=None, port=0, daemon=None, ns=True, verbose=True):
        """
        Very basic method to fire up a daemon (or supply one yourself).
        objects is a dict containing objects to register as keys, and
        their names (or None) as values. If ns is true they will be registered
        in the naming server as well, otherwise they just stay local.
        """
        if not daemon:
            daemon=Daemon(host, port)
        with daemon:
            if ns:
                ns=Pyro4.naming.locateNS()
            for obj, name in objects.items():
                if ns:
                    localname=None   # name is used for the name server
                else:
                    localname=name   # no name server, use name in daemon
                uri=daemon.register(obj, localname)
                if verbose:
                    print("Object {0}:\n    uri = {1}".format(repr(obj), uri))
                if name and ns:
                    ns.register(name, uri)
                    if verbose:
                        print("    name = {0}".format(name))
            if verbose:
                print("Pyro daemon running.")
            daemon.requestLoop()

    def requestLoop(self, loopCondition=lambda: True):
        """
        Goes in a loop to service incoming requests, until someone breaks this
        or calls shutdown from another thread.
        """
        self.__mustshutdown.clear()
        log.info("daemon %s entering requestloop", self.locationStr)
        try:
            self.__loopstopped.clear()
            condition=lambda: not self.__mustshutdown.isSet() and loopCondition()
            self.transportServer.loop(loopCondition=condition)
        finally:
            self.__loopstopped.set()
        log.debug("daemon exits requestloop")

    def events(self, eventsockets):
        """for use in an external event loop: handle any requests that are pending for this daemon"""
        return self.transportServer.events(eventsockets)

    def shutdown(self):
        """Cleanly terminate a daemon that is running in the requestloop. It must be running
        in a different thread, or this method will deadlock."""
        log.debug("daemon shutting down")
        self.__mustshutdown.set()
        self.transportServer.wakeup()
        time.sleep(0.05)
        self.close()
        self.__loopstopped.wait()
        log.info("daemon %s shut down", self.locationStr)

    def _handshake(self, conn):
        """Perform connection handshake with new clients"""
        # For now, client is not sending anything. Just respond with a CONNECT_OK.
        # We need a minimal amount of data or the socket will remain blocked
        # on some systems... (messages smaller than 40 bytes)
        # Return True for successful handshake, False if something was wrong.
        # We default to the marshal serializer to send message payload of "ok"
        ser = util.get_serializer("marshal")
        data = ser.dumps("ok")
        msg = Message(Pyro4.message.MSG_CONNECTOK, data, ser.serializer_id, 0, 1)
        conn.send(msg.to_bytes())
        return True

    def handleRequest(self, conn):
        """
        Handle incoming Pyro request. Catches any exception that may occur and
        wraps it in a reply to the calling side, as to not make this server side loop
        terminate due to exceptions caused by remote invocations.
        """
        request_flags=0
        request_seq=0
        request_serializer_id = util.MarshalSerializer.serializer_id
        wasBatched=False
        isCallback=False
        try:
            msg = Message.recv(conn, [Pyro4.message.MSG_INVOKE, Pyro4.message.MSG_PING])
            request_flags = msg.flags
            request_seq = msg.seq
            request_serializer_id = msg.serializer_id
            if Pyro4.config.LOGWIRE:
                log.debug("daemon wiredata received: msgtype=%d flags=0x%x ser=%d seq=%d data=%r" % (msg.type, msg.flags, msg.serializer_id, msg.seq, msg.data) )
            if msg.type == Pyro4.message.MSG_PING:
                # return same seq, but ignore any data (it's a ping, not an echo). Nothing is deserialized.
                msg = Message(Pyro4.message.MSG_PING, b"pong", msg.serializer_id, 0, msg.seq)
                if Pyro4.config.LOGWIRE:
                    log.debug("daemon wiredata sending: msgtype=%d flags=0x%x ser=%d seq=%d data=%r" % (msg.type, msg.flags, msg.serializer_id, msg.seq, msg.data))
                conn.send(msg.to_bytes())
                return
            if msg.serializer_id not in self.__serializer_ids:
                raise errors.ProtocolError("message used serializer that is not accepted: %d" % msg.serializer_id)
            serializer = util.get_serializer_by_id(msg.serializer_id)
            objId, method, vargs, kwargs = serializer.deserializeCall(msg.data, compressed=msg.flags & Pyro4.message.FLAGS_COMPRESSED)
            del msg  # invite GC to collect the object, don't wait for out-of-scope
            obj = self.objectsById.get(objId)
            if obj is not None:
                if kwargs and sys.version_info<(2, 6, 5) and os.name!="java":
                    # Python before 2.6.5 doesn't accept unicode keyword arguments
                    kwargs = dict((str(k), kwargs[k]) for k in kwargs)
                if request_flags & Pyro4.message.FLAGS_BATCH:
                    # batched method calls, loop over them all and collect all results
                    data=[]
                    for method, vargs, kwargs in vargs:
                        method=util.resolveDottedAttribute(obj, method, Pyro4.config.DOTTEDNAMES)
                        try:
                            result=method(*vargs, **kwargs)   # this is the actual method call to the Pyro object
                        except Exception:
                            xt, xv = sys.exc_info()[0:2]
                            log.debug("Exception occurred while handling batched request: %s", xv)
                            xv._pyroTraceback=util.formatTraceback(detailed=Pyro4.config.DETAILED_TRACEBACK)
                            if sys.platform=="cli":
                                util.fixIronPythonExceptionForPickle(xv, True)  # piggyback attributes
                            data.append(futures._ExceptionWrapper(xv))
                            break   # stop processing the rest of the batch
                        else:
                            data.append(result)
                    wasBatched=True
                else:
                    # normal single method call
                    method=util.resolveDottedAttribute(obj, method, Pyro4.config.DOTTEDNAMES)
                    if request_flags & Pyro4.message.FLAGS_ONEWAY and Pyro4.config.ONEWAY_THREADED:
                        # oneway call to be run inside its own thread
                        thread=threadutil.Thread(target=method, args=vargs, kwargs=kwargs)
                        thread.setDaemon(True)
                        thread.start()
                    else:
                        isCallback=getattr(method, "_pyroCallback", False)
                        data=method(*vargs, **kwargs)   # this is the actual method call to the Pyro object
            else:
                log.debug("unknown object requested: %s", objId)
                raise errors.DaemonError("unknown object")
            if request_flags & Pyro4.message.FLAGS_ONEWAY:
                return   # oneway call, don't send a response
            else:
                data, compressed = serializer.serializeData(data, compress=Pyro4.config.COMPRESSION)
                response_flags=0
                if compressed:
                    response_flags |= Pyro4.message.FLAGS_COMPRESSED
                if wasBatched:
                    response_flags |= Pyro4.message.FLAGS_BATCH
                if Pyro4.config.LOGWIRE:
                    log.debug("daemon wiredata sending: msgtype=%d flags=0x%x ser=%d seq=%d data=%r" % (Pyro4.message.MSG_RESULT, response_flags, serializer.serializer_id, request_seq, data))
                msg = Message(Pyro4.message.MSG_RESULT, data, serializer.serializer_id, response_flags, request_seq)
                conn.send(msg.to_bytes())
        except Exception:
            xt, xv = sys.exc_info()[0:2]
            if xt is not errors.ConnectionClosedError:
                log.debug("Exception occurred while handling request: %r", xv)
                if not request_flags & Pyro4.message.FLAGS_ONEWAY:
                    # only return the error to the client if it wasn't a oneway call
                    tblines=util.formatTraceback(detailed=Pyro4.config.DETAILED_TRACEBACK)
                    self._sendExceptionResponse(conn, request_seq, request_serializer_id, xv, tblines)
            if isCallback or isinstance(xv, (errors.CommunicationError, errors.SecurityError)):
                raise       # re-raise if flagged as callback, communication or security error.

    def _sendExceptionResponse(self, connection, seq, serializer_id, exc_value, tbinfo):
        """send an exception back including the local traceback info"""
        exc_value._pyroTraceback=tbinfo
        if sys.platform=="cli":
            util.fixIronPythonExceptionForPickle(exc_value, True)  # piggyback attributes
        serializer = util.get_serializer_by_id(serializer_id)
        try:
            data, compressed = serializer.serializeData(exc_value)
        except:
            # the exception object couldn't be serialized, use a generic PyroError instead
            xt, xv, tb = sys.exc_info()
            msg = "Error serializing exception: %s. Original exception: %s: %s" % (str(xv), type(exc_value), str(exc_value))
            exc_value = errors.PyroError(msg)
            exc_value._pyroTraceback=tbinfo
            if sys.platform=="cli":
                util.fixIronPythonExceptionForPickle(exc_value, True)  # piggyback attributes
            data, compressed = serializer.serializeData(exc_value)
        flags = Pyro4.message.FLAGS_EXCEPTION
        if compressed:
            flags |= Pyro4.message.FLAGS_COMPRESSED
        if Pyro4.config.LOGWIRE:
            log.debug("daemon wiredata sending (error response): msgtype=%d flags=0x%x ser=%d seq=%d data=%r" % (Pyro4.message.MSG_RESULT, flags, serializer.serializer_id, seq, data))
        msg = Message(Pyro4.message.MSG_RESULT, data, serializer.serializer_id, flags, seq)
        connection.send(msg.to_bytes())

    def register(self, obj, objectId=None):
        """
        Register a Pyro object under the given id. Note that this object is now only
        known inside this daemon, it is not automatically available in a name server.
        This method returns a URI for the registered object.
        """
        if objectId:
            if not isinstance(objectId, basestring):
                raise TypeError("objectId must be a string or None")
        else:
            objectId="obj_"+uuid.uuid4().hex   # generate a new objectId
        if hasattr(obj, "_pyroId") and obj._pyroId != "":     # check for empty string is needed for Cython
            raise errors.DaemonError("object already has a Pyro id")
        if objectId in self.objectsById:
            raise errors.DaemonError("object already registered with that id")
        # set some pyro attributes
        obj._pyroId=objectId
        obj._pyroDaemon=self
        if Pyro4.config.AUTOPROXY:
            # register a custom serializer for the type to automatically return proxies
            # we need to do this for all known serializers
            for ser in util._serializers.values():
                ser.register_type_replacement(type(obj), pyroObjectToAutoProxy)
        # register the object in the mapping
        self.objectsById[obj._pyroId]=obj
        return self.uriFor(objectId)

    def unregister(self, objectOrId):
        """
        Remove an object from the known objects inside this daemon.
        You can unregister an object directly or with its id.
        """
        if objectOrId is None:
            raise ValueError("object or objectid argument expected")
        if not isinstance(objectOrId, basestring):
            objectId=getattr(objectOrId, "_pyroId", None)
            if objectId is None:
                raise errors.DaemonError("object isn't registered")
        else:
            objectId=objectOrId
            objectOrId=None
        if objectId==constants.DAEMON_NAME:
            return
        if objectId in self.objectsById:
            del self.objectsById[objectId]
            if objectOrId is not None:
                del objectOrId._pyroId
                del objectOrId._pyroDaemon
                # Don't remove the custom type serializer because there may be
                # other registered objects of the same type still depending on it.

    def uriFor(self, objectOrId=None, nat=True):
        """
        Get a URI for the given object (or object id) from this daemon.
        Only a daemon can hand out proper uris because the access location is
        contained in them.
        Note that unregistered objects cannot be given an uri, but unregistered
        object names can (it's just a string we're creating in that case).
        If nat is set to False, the configured NAT address (if any) is ignored and it will
        return an URI for the internal address.
        """
        if not isinstance(objectOrId, basestring):
            objectOrId=getattr(objectOrId, "_pyroId", None)
            if objectOrId is None:
                raise errors.DaemonError("object isn't registered")
        if nat:
            loc=self.natLocationStr or self.locationStr
        else:
            loc=self.locationStr
        return URI("PYRO:%s@%s" % (objectOrId, loc))

    def close(self):
        """Close down the server and release resources"""
        log.debug("daemon closing")
        if self.transportServer:
            self.transportServer.close()
            self.transportServer=None

    def __repr__(self):
        return "<%s.%s at 0x%x, %s, %d objects>" % (self.__class__.__module__, self.__class__.__name__,
               id(self), self.locationStr, len(self.objectsById))

    def __enter__(self):
        if not self.transportServer:
            raise errors.PyroError("cannot reuse this object")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __getstate__(self):
        return {}   # a little hack to make it possible to serialize Pyro objects, because they can reference a daemon

    def __getstate_for_dict__(self):
        return self.__getstate__()


# decorators

def callback(object):
    """
    decorator to mark a method to be a 'callback'. This will make Pyro
    raise any errors also on the callback side, and not only on the side
    that does the callback call.
    """
    object._pyroCallback=True
    return object


try:
    import serpent
    def pyro_class_serpent_serializer(obj, serializer, stream, level):
        # Override the default way that a Pyro URI/proxy/daemon is serialized.
        # Because it defines a __getstate__ it would otherwise just become a tuple,
        # and not be deserialized as a class.
        d = Pyro4.util.SerializerBase.class_to_dict(obj)
        serializer.ser_builtins_dict(d, stream, level)
    serpent.register_class(URI, pyro_class_serpent_serializer)
    serpent.register_class(Proxy, pyro_class_serpent_serializer)
    serpent.register_class(Daemon, pyro_class_serpent_serializer)
    serpent.register_class(futures._ExceptionWrapper, pyro_class_serpent_serializer)
except ImportError:
    pass


def serialize_core_object_to_dict(obj):
    return {
        "__class__": "Pyro4.core." + obj.__class__.__name__,
        "state": obj.__getstate_for_dict__()
    }

Pyro4.util.SerializerBase.register_class_to_dict(URI, serialize_core_object_to_dict)
Pyro4.util.SerializerBase.register_class_to_dict(Proxy, serialize_core_object_to_dict)
Pyro4.util.SerializerBase.register_class_to_dict(Daemon, serialize_core_object_to_dict)
Pyro4.util.SerializerBase.register_class_to_dict(futures._ExceptionWrapper, futures._ExceptionWrapper.__serialized_dict__)
