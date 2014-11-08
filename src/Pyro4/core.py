"""
Core logic (uri, daemon, proxy stuff).

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import inspect
import re
import logging
import sys
import time
import os
import uuid
import warnings
import base64
import Pyro4.futures
from Pyro4 import errors, threadutil, socketutil, util, constants, message
from Pyro4.socketserver.threadpoolserver import SocketServer_Threadpool
from Pyro4.socketserver.multiplexserver import SocketServer_Poll, SocketServer_Select


__all__ = ["URI", "Proxy", "Daemon", "callback", "batch", "async", "expose", "oneway"]

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
            state = uri.__getstate__()
            self.__setstate__(state)
            return
        if not isinstance(uri, basestring):
            raise TypeError("uri parameter object is of wrong type")
        self.sockname = self.host = self.port = None
        match = self.uriRegEx.match(uri)
        if not match:
            raise errors.PyroError("invalid uri")
        self.protocol = match.group("protocol").upper()
        self.object = match.group("object")
        location = match.group("location")
        if self.protocol == "PYRONAME":
            self._parseLocation(location, Pyro4.config.NS_PORT)
            return
        if self.protocol == "PYRO":
            if not location:
                raise errors.PyroError("invalid uri")
            self._parseLocation(location, None)
        else:
            raise errors.PyroError("invalid uri (protocol)")

    def _parseLocation(self, location, defaultPort):
        if not location:
            return
        if location.startswith("./u:"):
            self.sockname = location[4:]
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
                self.port = defaultPort
            try:
                self.port = int(self.port)
            except (ValueError, TypeError):
                raise errors.PyroError("invalid port in uri, port=" + str(self.port))

    @staticmethod
    def isUnixsockLocation(location):
        """determine if a location string is for a Unix domain socket"""
        return location.startswith("./u:")

    @property
    def location(self):
        """property containing the location string, for instance ``"servername.you.com:5555"``"""
        if self.host:
            if ":" in self.host:  # ipv6
                return "[%s]:%d" % (self.host, self.port)
            else:
                return "%s:%d" % (self.host, self.port)
        elif self.sockname:
            return "./u:" + self.sockname
        else:
            return None

    def asString(self):
        """the string representation of this object"""
        result = self.protocol + ":" + self.object
        location = self.location
        if location:
            result += "@" + location
        return result

    def __str__(self):
        string = self.asString()
        if sys.version_info < (3, 0) and type(string) is unicode:
            return string.encode("ascii", "replace")
        return string

    def __unicode__(self):
        return self.asString()

    def __repr__(self):
        return "<%s.%s at 0x%x, %s>" % (self.__class__.__module__, self.__class__.__name__, id(self), str(self))

    def __eq__(self, other):
        if not isinstance(other, URI):
            return False
        return (self.protocol, self.object, self.sockname, self.host, self.port) == (other.protocol, other.object, other.sockname, other.host, other.port)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.protocol, self.object, self.sockname, self.host, self.port))

    # note: getstate/setstate are not needed if we use pickle protocol 2,
    # but this way it helps pickle to make the representation smaller by omitting all attribute names.

    def __getstate__(self):
        return self.protocol, self.object, self.sockname, self.host, self.port

    def __setstate__(self, state):
        self.protocol, self.object, self.sockname, self.host, self.port = state

    def __getstate_for_dict__(self):
        return self.__getstate__()

    def __setstate_from_dict__(self, state):
        self.__setstate__(state)


class _RemoteMethod(object):
    """method call abstraction"""

    def __init__(self, send, name):
        self.__send = send
        self.__name = name

    def __getattr__(self, name):
        return _RemoteMethod(self.__send, "%s.%s" % (self.__name, name))

    def __call__(self, *args, **kwargs):
        return self.__send(self.__name, args, kwargs)


class Proxy(object):
    """
    Pyro proxy for a remote object. Intercepts method calls and dispatches them to the remote object.

    .. automethod:: _pyroBind
    .. automethod:: _pyroRelease
    .. automethod:: _pyroReconnect
    .. automethod:: _pyroBatch
    .. automethod:: _pyroAsync
    """
    __pyroAttributes = frozenset(
        ["__getnewargs__", "__getnewargs_ex__", "__getinitargs__", "_pyroConnection", "_pyroUri",
         "_pyroOneway", "_pyroMethods", "_pyroAttrs", "_pyroTimeout", "_pyroSeq", "_pyroHmacKey",
         "_Proxy__pyroHmacKey", "_Proxy__pyroTimeout", "_Proxy__pyroLock", "_Proxy__pyroConnLock"])

    def __init__(self, uri):
        """
        .. autoattribute:: _pyroTimeout
        """
        if isinstance(uri, basestring):
            uri = URI(uri)
        elif not isinstance(uri, URI):
            raise TypeError("expected Pyro URI")
        self._pyroUri = uri
        self._pyroConnection = None
        self._pyroMethods = set()  # all methods of the remote object, gotten from meta-data
        self._pyroAttrs = set()  # attributes of the remote object, gotten from meta-data
        self._pyroOneway = set()  # oneway-methods of the remote object, gotten from meta-data
        self._pyroSeq = 0  # message sequence number
        self.__pyroHmacKey = None
        self.__pyroTimeout = Pyro4.config.COMMTIMEOUT
        self.__pyroLock = threadutil.Lock()
        self.__pyroConnLock = threadutil.Lock()
        util.get_serializer(Pyro4.config.SERIALIZER)  # assert that the configured serializer is available
        if os.name == "java" and Pyro4.config.SERIALIZER == "marshal":
            warnings.warn("marshal doesn't work correctly with Jython (issue 2077); please choose another serializer", RuntimeWarning)

    @property
    def _pyroHmacKey(self):
        return self.__pyroHmacKey

    @_pyroHmacKey.setter
    def _pyroHmacKey(self, value):
        # if needed, convert the hmac value to bytes first
        if value and sys.version_info >= (3, 0) and type(value) is not bytes:
            value = value.encode("utf-8")  # convert to bytes
        self.__pyroHmacKey = value

    def __del__(self):
        if hasattr(self, "_pyroConnection"):
            self._pyroRelease()

    def __getattr__(self, name):
        if name in Proxy.__pyroAttributes:
            # allows it to be safely pickled
            raise AttributeError(name)
        if Pyro4.config.METADATA:
            # get metadata if it's not there yet
            if not self._pyroMethods and not self._pyroAttrs:
                self._pyroGetMetadata()
        if name in self._pyroAttrs:
            return self._pyroInvoke("__getattr__", (name,), None)
        if Pyro4.config.METADATA and name not in self._pyroMethods:
            # client side check if the requested attr actually exists
            raise AttributeError("remote object '%s' has no exposed attribute or method '%s'" % (self._pyroUri, name))
        return _RemoteMethod(self._pyroInvoke, name)
    
    def __setattr__(self, name, value):
        if name in Proxy.__pyroAttributes:
            return super(Proxy, self).__setattr__(name, value)  # one of the special pyro attributes
        if name in self._pyroAttrs:
            return self._pyroInvoke("__setattr__", (name, value), None)  # remote attribute
        if Pyro4.config.METADATA:
            # client side validation if the requested attr actually exists
            raise AttributeError("remote object '%s' has no exposed attribute '%s'" % (self._pyroUri, name))
        # metadata disabled, just treat it as a local attribute on the proxy:
        return super(Proxy, self).__setattr__(name, value)

    def __repr__(self):
        connected = "connected" if self._pyroConnection else "not connected"
        return "<%s.%s at 0x%x, %s, for %s>" % (self.__class__.__module__, self.__class__.__name__,
                                                id(self), connected, self._pyroUri)

    def __unicode__(self):
        return str(self)

    def __getstate_for_dict__(self):
        encodedHmac = None
        if self._pyroHmacKey is not None:
            if sys.platform == 'cli' and type(self._pyroHmacKey) is bytes:
                # ironpython doesn't grok bytes for b64encode
                self._pyroHmacKey = str(self._pyroHmacKey)
            encodedHmac = "b64:"+(base64.b64encode(self._pyroHmacKey).decode("ascii"))
        return self._pyroUri.asString(), tuple(self._pyroOneway), tuple(self._pyroMethods), tuple(self._pyroAttrs),\
            self.__pyroTimeout, encodedHmac

    def __setstate_from_dict__(self, state):
        uri = URI(state[0])
        oneway = set(state[1])
        methods = set(state[2])
        attrs = set(state[3])
        timeout = state[4]
        hmac_key = state[5]
        if hmac_key:
            if hmac_key.startswith("b64:"):
                hmac_key = base64.b64decode(hmac_key[4:].encode("ascii"))
            else:
                raise errors.ProtocolError("hmac encoding error")
        self.__setstate__((uri, oneway, methods, attrs, timeout, hmac_key))

    def __getstate__(self):
        return self._pyroUri, self._pyroOneway, self._pyroMethods, self._pyroAttrs, self.__pyroTimeout, self._pyroHmacKey  # skip the connection

    def __setstate__(self, state):
        self._pyroUri, self._pyroOneway, self._pyroMethods, self._pyroAttrs, self.__pyroTimeout, self._pyroHmacKey = state
        self._pyroConnection = None
        self._pyroSeq = 0
        self.__pyroLock = threadutil.Lock()
        self.__pyroConnLock = threadutil.Lock()

    def __copy__(self):
        uriCopy = URI(self._pyroUri)
        p = Proxy(uriCopy)
        p._pyroOneway = set(self._pyroOneway)
        p._pyroMethods = set(self._pyroMethods)
        p._pyroAttrs = set(self._pyroAttrs)
        p._pyroTimeout = self._pyroTimeout
        p._pyroHmacKey = self._pyroHmacKey
        return p

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._pyroRelease()

    def __eq__(self, other):
        if other is self:
            return True
        return isinstance(other, Proxy) and other._pyroUri == self._pyroUri

    def __ne__(self, other):
        if other and isinstance(other, Proxy):
            return other._pyroUri != self._pyroUri
        return True

    def __hash__(self):
        return hash(self._pyroUri)

    def __dir__(self):
        result = dir(self.__class__) + list(self.__dict__.keys())
        return sorted(set(result) | self._pyroMethods | self._pyroAttrs)

    def _pyroRelease(self):
        """release the connection to the pyro daemon"""
        with self.__pyroConnLock:
            if self._pyroConnection is not None:
                self._pyroConnection.close()
                self._pyroConnection = None
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
        self.__pyroTimeout = timeout
        if self._pyroConnection is not None:
            self._pyroConnection.timeout = timeout

    _pyroTimeout = property(__pyroGetTimeout, __pyroSetTimeout)

    def _pyroInvoke(self, methodname, vargs, kwargs, flags=0, objectId=None):
        """perform the remote method call communication"""
        if self._pyroConnection is None:
            # rebind here, don't do it from inside the invoke because deadlock will occur
            self.__pyroCreateConnection()
        serializer = util.get_serializer(Pyro4.config.SERIALIZER)
        data, compressed = serializer.serializeCall(
            objectId or self._pyroConnection.objectId, methodname, vargs, kwargs,
            compress=Pyro4.config.COMPRESSION)
        if compressed:
            flags |= Pyro4.message.FLAGS_COMPRESSED
        if methodname in self._pyroOneway:
            flags |= Pyro4.message.FLAGS_ONEWAY
        with self.__pyroLock:
            self._pyroSeq = (self._pyroSeq + 1) & 0xffff
            if Pyro4.config.LOGWIRE:
                log.debug("proxy wiredata sending: msgtype=%d flags=0x%x ser=%d seq=%d data=%r" %
                          (message.MSG_INVOKE, flags, serializer.serializer_id, self._pyroSeq, data))
            msg = message.Message(message.MSG_INVOKE, data, serializer.serializer_id, flags, self._pyroSeq, hmac_key=self._pyroHmacKey)
            try:
                self._pyroConnection.send(msg.to_bytes())
                del msg  # invite GC to collect the object, don't wait for out-of-scope
                if flags & message.FLAGS_ONEWAY:
                    return None  # oneway call, no response data
                else:
                    msg = message.Message.recv(self._pyroConnection, [message.MSG_RESULT], hmac_key=self._pyroHmacKey)
                    if Pyro4.config.LOGWIRE:
                        log.debug("proxy wiredata received: msgtype=%d flags=0x%x ser=%d seq=%d data=%r" % (msg.type, msg.flags, msg.serializer_id, msg.seq, msg.data))
                    self.__pyroCheckSequence(msg.seq)
                    if msg.serializer_id != serializer.serializer_id:
                        error = "invalid serializer in response: %d" % msg.serializer_id
                        log.error(error)
                        raise errors.ProtocolError(error)
                    data = serializer.deserializeData(msg.data, compressed=msg.flags & message.FLAGS_COMPRESSED)
                    if msg.flags & message.FLAGS_EXCEPTION:
                        if sys.platform == "cli":
                            util.fixIronPythonExceptionForPickle(data, False)
                        raise data
                    else:
                        return data
            except (errors.CommunicationError, KeyboardInterrupt):
                # Communication error during read. To avoid corrupt transfers, we close the connection.
                # Otherwise we might receive the previous reply as a result of a new method call!
                # Special case for keyboardinterrupt: people pressing ^C to abort the client
                # may be catching the keyboardinterrupt in their code. We should probably be on the
                # safe side and release the proxy connection in this case too, because they might
                # be reusing the proxy object after catching the exception...
                self._pyroRelease()
                raise

    def __pyroCheckSequence(self, seq):
        if seq != self._pyroSeq:
            err = "invoke: reply sequence out of sync, got %d expected %d" % (seq, self._pyroSeq)
            log.error(err)
            raise errors.ProtocolError(err)

    def __pyroCreateConnection(self, replaceUri=False):
        """
        Connects this proxy to the remote Pyro daemon. Does connection handshake.
        Returns true if a new connection was made, false if an existing one was already present.
        """
        with self.__pyroConnLock:
            if self._pyroConnection is not None:
                return False  # already connected
            from Pyro4.naming import resolve  # don't import this globally because of cyclic dependency
            uri = resolve(self._pyroUri)
            # socket connection (normal or Unix domain socket)
            conn = None
            log.debug("connecting to %s", uri)
            connect_location = uri.sockname or (uri.host, uri.port)
            with self.__pyroLock:
                try:
                    if self._pyroConnection is not None:
                        return False  # already connected
                    sock = socketutil.createSocket(connect=connect_location, reuseaddr=Pyro4.config.SOCK_REUSE, timeout=self.__pyroTimeout)
                    conn = socketutil.SocketConnection(sock, uri.object)
                    # Do handshake. For now, no need to send anything. (message type CONNECT is not yet used)
                    msg = message.Message.recv(conn, None, hmac_key=self._pyroHmacKey)
                    # any trailing data (dataLen>0) is an error message, if any
                except Exception:
                    x = sys.exc_info()[1]
                    if conn:
                        conn.close()
                    err = "cannot connect: %s" % x
                    log.error(err)
                    if isinstance(x, errors.CommunicationError):
                        raise
                    else:
                        ce = errors.CommunicationError(err)
                        ce.__cause__ = x
                        raise ce
                else:
                    if msg.type == message.MSG_CONNECTFAIL:
                        error = "connection rejected"
                        if msg.data:
                            serializer = util.get_serializer_by_id(msg.serializer_id)
                            data = serializer.deserializeData(msg.data, compressed=msg.flags & Pyro4.message.FLAGS_COMPRESSED)
                            error += ", reason: " + data
                        conn.close()
                        log.error(error)
                        raise errors.CommunicationError(error)
                    if msg.type != message.MSG_CONNECTOK:
                        conn.close()
                        err = "connect: invalid msg type %d received" % msg.type
                        log.error(err)
                        raise errors.ProtocolError(err)
                    self._pyroConnection = conn
                    if replaceUri:
                        self._pyroUri = uri
                    log.debug("connected to %s", self._pyroUri)
            if Pyro4.config.METADATA:
                # obtain metadata if this feature is enabled, and the metadata is not known yet
                if self._pyroMethods or self._pyroAttrs:
                    log.debug("reusing existing metadata")
                else:
                    self._pyroGetMetadata(uri.object)
            return True

    def _pyroGetMetadata(self, objectId=None, known_metadata=None):
        """get metadata from server (methods, attrs, oneway, ...) and remember them in some attributes of the proxy"""
        objectId = objectId or self._pyroUri.object
        log.debug("getting metadata for object %s", objectId)
        if self._pyroConnection is None and not known_metadata:
            try:
                self.__pyroCreateConnection()
            except errors.PyroError:
                log.error("problem getting metadata: cannot connect")
                raise
            if self._pyroMethods or self._pyroAttrs:
                return  # metadata has already been retrieved as part of creating the connection
        try:
            # invoke the get_metadata method on the daemon
            result = known_metadata or self._pyroInvoke("get_metadata", [objectId], {}, objectId=constants.DAEMON_NAME)
            self._pyroOneway = set(result["oneway"])
            self._pyroMethods = set(result["methods"])
            self._pyroAttrs = set(result["attrs"])
            if log.isEnabledFor(logging.DEBUG):
                log.debug("from meta: oneway methods=%s", sorted(self._pyroOneway))
                log.debug("from meta: methods=%s", sorted(self._pyroMethods))
                log.debug("from meta: attributes=%s", sorted(self._pyroAttrs))
            if not self._pyroMethods and not self._pyroAttrs:
                raise errors.PyroError("remote object doesn't expose any methods or attributes")
        except errors.PyroError as x:
            log.error("problem getting metadata: %r", x)
            raise

    def _pyroReconnect(self, tries=100000000):
        """
        (Re)connect the proxy to the daemon containing the pyro object which the proxy is for.
        In contrast to the _pyroBind method, this one first releases the connection (if the proxy is still connected)
        and retries making a new connection until it succeeds or the given amount of tries ran out.
        """
        self._pyroRelease()
        while tries:
            try:
                self.__pyroCreateConnection()
                return
            except errors.CommunicationError:
                tries -= 1
                if tries:
                    time.sleep(2)
        msg = "failed to reconnect"
        log.error(msg)
        raise errors.ConnectionClosedError(msg)

    def _pyroBatch(self):
        """returns a helper class that lets you create batched method calls on the proxy"""
        return _BatchProxyAdapter(self)

    def _pyroAsync(self):
        """returns a helper class that lets you do asynchronous method calls on the proxy"""
        return _AsyncProxyAdapter(self)

    def _pyroInvokeBatch(self, calls, oneway=False):
        flags = Pyro4.message.FLAGS_BATCH
        if oneway:
            flags |= Pyro4.message.FLAGS_ONEWAY
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
    carry out the batched calls. Call methods on this object that you want to batch,
    and finally call the batch proxy itself. That call will return a generator
    for the results of every method call in the batch (in sequence)."""

    def __init__(self, proxy):
        self.__proxy = proxy
        self.__calls = []

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
            if isinstance(result, Pyro4.futures._ExceptionWrapper):
                result.raiseIt()  # re-raise the remote exception locally.
            else:
                yield result  # it is a regular result object, yield that and continue.

    def __call__(self, oneway=False, async=False):
        if oneway and async:
            raise errors.PyroError("async oneway calls make no sense")
        if async:
            return _AsyncRemoteMethod(self, "<asyncbatch>")()
        else:
            results = self.__proxy._pyroInvokeBatch(self.__calls, oneway)
            self.__calls = []  # clear for re-use
            if not oneway:
                return self.__resultsgenerator(results)

    def _pyroInvoke(self, name, args, kwargs):
        # ignore all parameters, we just need to execute the batch
        results = self.__proxy._pyroInvokeBatch(self.__calls)
        self.__calls = []  # clear for re-use
        return self.__resultsgenerator(results)


class _AsyncProxyAdapter(object):
    def __init__(self, proxy):
        self.__proxy = proxy

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
        result = Pyro4.futures.FutureResult()
        thread = threadutil.Thread(target=self.__asynccall, args=(result, args, kwargs))
        thread.setDaemon(True)
        thread.start()
        return result

    def __asynccall(self, asyncresult, args, kwargs):
        try:
            # use a copy of the proxy otherwise calls would be serialized,
            # and use contextmanager to close the proxy after we're done
            with self.__proxy.__copy__() as proxy:
                value = proxy._pyroInvoke(self.__name, args, kwargs)
            asyncresult.value = value
        except Exception:
            # ignore any exceptions here, return them as part of the async result instead
            asyncresult.value = Pyro4.futures._ExceptionWrapper(sys.exc_info()[1])


def batch(proxy):
    """convenience method to get a batch proxy adapter"""
    return proxy._pyroBatch()


def async(proxy):
    """convenience method to get an async proxy adapter"""
    return proxy._pyroAsync()


def pyroObjectToAutoProxy(obj):
    """reduce function that automatically replaces Pyro objects by a Proxy"""
    if Pyro4.config.AUTOPROXY:
        daemon = getattr(obj, "_pyroDaemon", None)
        if daemon:
            # only return a proxy if the object is a registered pyro object
            return daemon.proxyFor(obj)
    return obj


# decorators

def callback(method):
    """
    decorator to mark a method to be a 'callback'. This will make Pyro
    raise any errors also on the callback side, and not only on the side
    that does the callback call.
    """
    method._pyroCallback = True
    return method


def oneway(method):
    """
    decorator to mark a method to be oneway (client won't wait for a response)
    """
    method._pyroOneway = True
    return method


def expose(method_or_class):
    """
    decorator to mark a method or class to be exposed for remote calls (relevant if REQUIRE_EXPOSE=True)
    """
    if inspect.isdatadescriptor(method_or_class):
        func = method_or_class.fget or method_or_class.fset or method_or_class.fdel
        if util.is_private_attribute(func.__name__):
            raise AttributeError("exposing private names (starting with _) is not allowed")
        func._pyroExposed = True
        return method_or_class
    if util.is_private_attribute(method_or_class.__name__):
        raise AttributeError("exposing private names (starting with _) is not allowed")
    if inspect.isclass(method_or_class):
        log.debug("exposing all members of %r", method_or_class)
        for name in method_or_class.__dict__:
            if util.is_private_attribute(name):
                continue
            thing = getattr(method_or_class, name)
            if inspect.isfunction(thing):
                thing._pyroExposed = True
            elif inspect.ismethod(thing):
                thing.__func__._pyroExposed = True
            elif inspect.isdatadescriptor(thing):
                if getattr(thing, "fset", None):
                    thing.fset._pyroExposed = True
                if getattr(thing, "fget", None):
                    thing.fget._pyroExposed = True
                if getattr(thing, "fdel", None):
                    thing.fdel._pyroExposed = True
    method_or_class._pyroExposed = True
    return method_or_class


@expose
class DaemonObject(object):
    """The part of the daemon that is exposed as a Pyro object."""

    def __init__(self, daemon):
        self.daemon = daemon

    def registered(self):
        """returns a list of all object names registered in this daemon"""
        return list(self.daemon.objectsById.keys())

    def ping(self):
        """a simple do-nothing method for testing purposes"""
        pass

    def info(self):
        """return some descriptive information about the daemon"""
        return "%s bound on %s, NAT %s, %d objects registered. Servertype: %s" % (
            constants.DAEMON_NAME, self.daemon.locationStr, self.daemon.natLocationStr,
            len(self.daemon.objectsById), self.daemon.transportServer)

    def get_metadata(self, objectId):
        """
        Get metadata for the given object (exposed methods, oneways, attributes).
        If you get an error in your proxy saying that 'DaemonObject' has no attribute 'get_metdata',
        you're probably connecting to an older Pyro version (4.26 or earlier).
        Either upgrade the Pyro version or set METDATA config item to False in your client code.
        """
        obj = self.daemon.objectsById.get(objectId)
        if obj is not None:
            return util.get_exposed_members(obj, only_exposed=Pyro4.config.REQUIRE_EXPOSE)
        else:
            log.debug("unknown object requested: %s", objectId)
            raise errors.DaemonError("unknown object")


class Daemon(object):
    """
    Pyro daemon. Contains server side logic and dispatches incoming remote method calls
    to the appropriate objects.
    """

    def __init__(self, host=None, port=0, unixsocket=None, nathost=None, natport=None, interface=DaemonObject):
        if host is None:
            host = Pyro4.config.HOST
        if nathost is None:
            nathost = Pyro4.config.NATHOST
        if natport is None:
            natport = Pyro4.config.NATPORT or None
        if nathost and unixsocket:
            raise ValueError("cannot use nathost together with unixsocket")
        if (nathost is None) ^ (natport is None):
            raise ValueError("must provide natport with nathost")
        if Pyro4.config.SERVERTYPE == "thread":
            self.transportServer = SocketServer_Threadpool()
        elif Pyro4.config.SERVERTYPE == "multiplex":
            # choose the 'best' multiplexing implementation
            if os.name == "java":
                self.transportServer = SocketServer_Select()  # poll doesn't work as given in jython ('socket must be in nonblocking mode')
            else:
                self.transportServer = SocketServer_Poll() if socketutil.hasPoll else SocketServer_Select()
        else:
            raise errors.PyroError("invalid server type '%s'" % Pyro4.config.SERVERTYPE)
        self.transportServer.init(self, host, port, unixsocket)
        #: The location (str of the form ``host:portnumber``) on which the Daemon is listening
        self.locationStr = self.transportServer.locationStr
        log.debug("created daemon on %s", self.locationStr)
        natport_for_loc = natport
        if natport == 0:
            # expose internal port number as NAT port as well. (don't use port because it could be 0 and will be chosen by the OS)
            natport_for_loc = int(self.locationStr.split(":")[1])
        #: The NAT-location (str of the form ``nathost:natportnumber``) on which the Daemon is exposed for use with NAT-routing
        self.natLocationStr = "%s:%d" % (nathost, natport_for_loc) if nathost else None
        if self.natLocationStr:
            log.debug("NAT address is %s", self.natLocationStr)
        pyroObject = interface(self)
        pyroObject._pyroId = constants.DAEMON_NAME
        #: Dictionary from Pyro object id to the actual Pyro object registered by this id
        self.objectsById = {pyroObject._pyroId: pyroObject}
        self.__mustshutdown = threadutil.Event()
        self.__loopstopped = threadutil.Event()
        self.__loopstopped.set()
        # assert that the configured serializers are available, and remember their ids:
        self.__serializer_ids = set([util.get_serializer(ser_name).serializer_id for ser_name in Pyro4.config.SERIALIZERS_ACCEPTED])
        log.debug("accepted serializers: %s" % Pyro4.config.SERIALIZERS_ACCEPTED)
        log.debug("pyro protocol version: %d  pickle version: %d" % (constants.PROTOCOL_VERSION, Pyro4.config.PICKLE_PROTOCOL_VERSION))
        self.__pyroHmacKey = None

    @property
    def _pyroHmacKey(self):
        return self.__pyroHmacKey

    @_pyroHmacKey.setter
    def _pyroHmacKey(self, value):
        # if needed, convert the hmac value to bytes first
        if value and sys.version_info >= (3, 0) and type(value) is not bytes:
            value = value.encode("utf-8")  # convert to bytes
        self.__pyroHmacKey = value

    @property
    def sock(self):
        return self.transportServer.sock

    @property
    def sockets(self):
        return self.transportServer.sockets

    @staticmethod
    def serveSimple(objects, host=None, port=0, daemon=None, ns=True, verbose=True):
        """
        Basic method to fire up a daemon (or supply one yourself).
        objects is a dict containing objects to register as keys, and
        their names (or None) as values. If ns is true they will be registered
        in the naming server as well, otherwise they just stay local.
        See the documentation on 'publishing objects' (in chapter: Servers) for more details.
        """
        if daemon is None:
            daemon = Daemon(host, port)
        with daemon:
            if ns:
                ns = Pyro4.naming.locateNS()
            for obj, name in objects.items():
                if ns:
                    localname = None  # name is used for the name server
                else:
                    localname = name  # no name server, use name in daemon
                uri = daemon.register(obj, localname)
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
            condition = lambda: not self.__mustshutdown.isSet() and loopCondition()
            self.transportServer.loop(loopCondition=condition)
        finally:
            self.__loopstopped.set()
        log.debug("daemon exits requestloop")

    def events(self, eventsockets):
        """for use in an external event loop: handle any requests that are pending for this daemon"""
        return self.transportServer.events(eventsockets)

    def shutdown(self):
        """Cleanly terminate a daemon that is running in the requestloop."""
        log.debug("daemon shutting down")

        def shutdown_thread():
            time.sleep(0.05)
            self.__mustshutdown.set()
            self.transportServer.wakeup()
            time.sleep(0.05)
            self.close()
            self.__loopstopped.wait(timeout=5)  # use timeout to avoid deadlock situations
            log.info("daemon %s shut down", self.locationStr)

        # We do the actual shutdown from a separate thread so that any Pyro method
        # that may be calling this, can return its response normally without directly
        # severing the socket and causing a ConnectionClosedError on the proxy.
        thread = threadutil.Thread(target=shutdown_thread)
        thread.start()

    def _handshake(self, conn):
        """Perform connection handshake with new clients"""
        # For now, client is not sending anything. Just respond with a CONNECT_OK.
        # We need a minimal amount of data or the socket will remain blocked
        # on some systems... (messages smaller than 40 bytes)
        # Return True for successful handshake, False if something was wrong.
        # We default to the marshal serializer to send message payload of "ok"
        ser = util.get_serializer("marshal")
        data = ser.dumps("ok")
        msg = message.Message(message.MSG_CONNECTOK, data, ser.serializer_id, 0, 1, hmac_key=self._pyroHmacKey)
        conn.send(msg.to_bytes())
        return True

    def handleRequest(self, conn):
        """
        Handle incoming Pyro request. Catches any exception that may occur and
        wraps it in a reply to the calling side, as to not make this server side loop
        terminate due to exceptions caused by remote invocations.
        """
        request_flags = 0
        request_seq = 0
        request_serializer_id = util.MarshalSerializer.serializer_id
        wasBatched = False
        isCallback = False
        try:
            msg = message.Message.recv(conn, [message.MSG_INVOKE, message.MSG_PING], hmac_key=self._pyroHmacKey)
            request_flags = msg.flags
            request_seq = msg.seq
            request_serializer_id = msg.serializer_id
            if Pyro4.config.LOGWIRE:
                log.debug("daemon wiredata received: msgtype=%d flags=0x%x ser=%d seq=%d data=%r" % (msg.type, msg.flags, msg.serializer_id, msg.seq, msg.data))
            if msg.type == message.MSG_PING:
                # return same seq, but ignore any data (it's a ping, not an echo). Nothing is deserialized.
                msg = message.Message(message.MSG_PING, b"pong", msg.serializer_id, 0, msg.seq, hmac_key=self._pyroHmacKey)
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
                if kwargs and sys.version_info < (2, 6, 5) and os.name != "java":
                    # Python before 2.6.5 doesn't accept unicode keyword arguments
                    kwargs = dict((str(k), kwargs[k]) for k in kwargs)
                if request_flags & Pyro4.message.FLAGS_BATCH:
                    # batched method calls, loop over them all and collect all results
                    data = []
                    for method, vargs, kwargs in vargs:
                        method = util.getAttribute(obj, method)
                        try:
                            result = method(*vargs, **kwargs)  # this is the actual method call to the Pyro object
                        except Exception:
                            xt, xv = sys.exc_info()[0:2]
                            log.debug("Exception occurred while handling batched request: %s", xv)
                            xv._pyroTraceback = util.formatTraceback(detailed=Pyro4.config.DETAILED_TRACEBACK)
                            if sys.platform == "cli":
                                util.fixIronPythonExceptionForPickle(xv, True)  # piggyback attributes
                            data.append(Pyro4.futures._ExceptionWrapper(xv))
                            break  # stop processing the rest of the batch
                        else:
                            data.append(result)
                    wasBatched = True
                else:
                    # normal single method call
                    if method == "__getattr__":
                        # special case for direct attribute access (only exposed @properties are accessible)
                        data = util.get_exposed_property_value(obj, vargs[0], only_exposed=Pyro4.config.REQUIRE_EXPOSE)
                    elif method == "__setattr__":
                        # special case for direct attribute access (only exposed @properties are accessible)
                        data = util.set_exposed_property_value(obj, vargs[0], vargs[1], only_exposed=Pyro4.config.REQUIRE_EXPOSE)
                    else:
                        method = util.getAttribute(obj, method)
                        if request_flags & Pyro4.message.FLAGS_ONEWAY and Pyro4.config.ONEWAY_THREADED:
                            # oneway call to be run inside its own thread
                            thread = threadutil.Thread(target=method, args=vargs, kwargs=kwargs)
                            thread.setDaemon(True)
                            thread.start()
                        else:
                            isCallback = getattr(method, "_pyroCallback", False)
                            data = method(*vargs, **kwargs)  # this is the actual method call to the Pyro object
            else:
                log.debug("unknown object requested: %s", objId)
                raise errors.DaemonError("unknown object")
            if request_flags & Pyro4.message.FLAGS_ONEWAY:
                return  # oneway call, don't send a response
            else:
                data, compressed = serializer.serializeData(data, compress=Pyro4.config.COMPRESSION)
                response_flags = 0
                if compressed:
                    response_flags |= Pyro4.message.FLAGS_COMPRESSED
                if wasBatched:
                    response_flags |= Pyro4.message.FLAGS_BATCH
                if Pyro4.config.LOGWIRE:
                    log.debug("daemon wiredata sending: msgtype=%d flags=0x%x ser=%d seq=%d data=%r" % (message.MSG_RESULT, response_flags, serializer.serializer_id, request_seq, data))
                msg = message.Message(message.MSG_RESULT, data, serializer.serializer_id, response_flags, request_seq, hmac_key=self._pyroHmacKey)
                conn.send(msg.to_bytes())
        except Exception:
            xt, xv = sys.exc_info()[0:2]
            if xt is not errors.ConnectionClosedError:
                log.debug("Exception occurred while handling request: %r", xv)
                if not request_flags & Pyro4.message.FLAGS_ONEWAY and not isinstance(xv, errors.CommunicationError):
                    # only return the error to the client if it wasn't a oneway call, and not a communication error
                    # (in these cases, it makes no sense to try to report the error back to the client...)
                    tblines = util.formatTraceback(detailed=Pyro4.config.DETAILED_TRACEBACK)
                    self._sendExceptionResponse(conn, request_seq, request_serializer_id, xv, tblines)
            if isCallback or isinstance(xv, (errors.CommunicationError, errors.SecurityError)):
                raise  # re-raise if flagged as callback, communication or security error.

    def _sendExceptionResponse(self, connection, seq, serializer_id, exc_value, tbinfo):
        """send an exception back including the local traceback info"""
        exc_value._pyroTraceback = tbinfo
        if sys.platform == "cli":
            util.fixIronPythonExceptionForPickle(exc_value, True)  # piggyback attributes
        serializer = util.get_serializer_by_id(serializer_id)
        try:
            data, compressed = serializer.serializeData(exc_value)
        except:
            # the exception object couldn't be serialized, use a generic PyroError instead
            xt, xv, tb = sys.exc_info()
            msg = "Error serializing exception: %s. Original exception: %s: %s" % (str(xv), type(exc_value), str(exc_value))
            exc_value = errors.PyroError(msg)
            exc_value._pyroTraceback = tbinfo
            if sys.platform == "cli":
                util.fixIronPythonExceptionForPickle(exc_value, True)  # piggyback attributes
            data, compressed = serializer.serializeData(exc_value)
        flags = Pyro4.message.FLAGS_EXCEPTION
        if compressed:
            flags |= Pyro4.message.FLAGS_COMPRESSED
        if Pyro4.config.LOGWIRE:
            log.debug("daemon wiredata sending (error response): msgtype=%d flags=0x%x ser=%d seq=%d data=%r" % (message.MSG_RESULT, flags, serializer.serializer_id, seq, data))
        msg = message.Message(message.MSG_RESULT, data, serializer.serializer_id, flags, seq, hmac_key=self._pyroHmacKey)
        connection.send(msg.to_bytes())

    def register(self, obj, objectId=None, force=False):
        """
        Register a Pyro object under the given id. Note that this object is now only
        known inside this daemon, it is not automatically available in a name server.
        This method returns a URI for the registered object.
        Pyro checks if an object is already registered, unless you set force=True.
        """
        if objectId:
            if not isinstance(objectId, basestring):
                raise TypeError("objectId must be a string or None")
        else:
            objectId = "obj_" + uuid.uuid4().hex  # generate a new objectId
        if not force:
            if hasattr(obj, "_pyroId") and obj._pyroId != "":  # check for empty string is needed for Cython
                raise errors.DaemonError("object already has a Pyro id")
            if objectId in self.objectsById:
                raise errors.DaemonError("an object was already registered with that id")
        # set some pyro attributes
        obj._pyroId = objectId
        obj._pyroDaemon = self
        if Pyro4.config.AUTOPROXY:
            # register a custom serializer for the type to automatically return proxies
            # we need to do this for all known serializers
            for ser in util._serializers.values():
                ser.register_type_replacement(type(obj), pyroObjectToAutoProxy)
        # register the object in the mapping
        self.objectsById[obj._pyroId] = obj
        return self.uriFor(objectId)

    def unregister(self, objectOrId):
        """
        Remove an object from the known objects inside this daemon.
        You can unregister an object directly or with its id.
        """
        if objectOrId is None:
            raise ValueError("object or objectid argument expected")
        if not isinstance(objectOrId, basestring):
            objectId = getattr(objectOrId, "_pyroId", None)
            if objectId is None:
                raise errors.DaemonError("object isn't registered")
        else:
            objectId = objectOrId
            objectOrId = None
        if objectId == constants.DAEMON_NAME:
            return
        if objectId in self.objectsById:
            del self.objectsById[objectId]
            if objectOrId is not None:
                del objectOrId._pyroId
                del objectOrId._pyroDaemon
                # Don't remove the custom type serializer because there may be
                # other registered objects of the same type still depending on it.

    def uriFor(self, objectOrId, nat=True):
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
            objectOrId = getattr(objectOrId, "_pyroId", None)
            if objectOrId is None or objectOrId not in self.objectsById:
                raise errors.DaemonError("object isn't registered in this daemon")
        if nat:
            loc = self.natLocationStr or self.locationStr
        else:
            loc = self.locationStr
        return URI("PYRO:%s@%s" % (objectOrId, loc))

    def proxyFor(self, objectOrId, nat=True):
        """
        Get a fully initialized Pyro Proxy for the given object (or object id) for this daemon.
        If nat is False, the configured NAT address (if any) is ignored.
        """
        uri = self.uriFor(objectOrId, nat)
        proxy = Proxy(uri)
        registered_object = self.objectsById.get(uri.object)
        if registered_object:
            meta = util.get_exposed_members(registered_object, only_exposed=Pyro4.config.REQUIRE_EXPOSE)
            proxy._pyroGetMetadata(known_metadata=meta)
        return proxy

    def close(self):
        """Close down the server and release resources"""
        log.debug("daemon closing")
        if self.transportServer:
            self.transportServer.close()
            self.transportServer = None

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
        return {}  # a little hack to make it possible to serialize Pyro objects, because they can reference a daemon

    def __getstate_for_dict__(self):
        return tuple(self.__getstate__())

    def __setstate_from_dict__(self, state):
        pass


# serpent serializer initialization

try:
    import serpent

    def pyro_class_serpent_serializer(obj, serializer, stream, level):
        # Override the default way that a Pyro URI/proxy/daemon is serialized.
        # Because it defines a __getstate__ it would otherwise just become a tuple,
        # and not be deserialized as a class.
        d = util.SerializerBase.class_to_dict(obj)
        serializer.ser_builtins_dict(d, stream, level)

    # register the special serializers for the pyro objects with Serpent
    serpent.register_class(URI, pyro_class_serpent_serializer)
    serpent.register_class(Proxy, pyro_class_serpent_serializer)
    serpent.register_class(Daemon, pyro_class_serpent_serializer)
    serpent.register_class(Pyro4.futures._ExceptionWrapper, pyro_class_serpent_serializer)
except ImportError:
    pass


def serialize_core_object_to_dict(obj):
    return {
        "__class__": "Pyro4.core." + obj.__class__.__name__,
        "state": obj.__getstate_for_dict__()
    }


util.SerializerBase.register_class_to_dict(URI, serialize_core_object_to_dict, serpent_too=False)
util.SerializerBase.register_class_to_dict(Proxy, serialize_core_object_to_dict, serpent_too=False)
util.SerializerBase.register_class_to_dict(Daemon, serialize_core_object_to_dict, serpent_too=False)
util.SerializerBase.register_class_to_dict(Pyro4.futures._ExceptionWrapper, Pyro4.futures._ExceptionWrapper.__serialized_dict__, serpent_too=False)
