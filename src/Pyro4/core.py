"""
Core logic (uri, daemon, proxy stuff).

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import print_function, division
import inspect
import re
import logging
import sys
import ssl
import os
import time
import threading
import uuid
import base64
import warnings
import socket
import random
from Pyro4 import errors, socketutil, util, constants, message, futures
from Pyro4.configuration import config


__all__ = ["URI", "Proxy", "Daemon", "current_context", "callback", "batch", "asyncproxy", "expose", "behavior",
           "oneway", "SerializedBlob", "_resolve", "_locateNS"]

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
    And one that looks up things in the name server by metadata:
      ``PYROMETA:meta1,meta2,...[@location]``  (optional name server location, can also omit location port)

    You can write the protocol in lowercase if you like (``pyro:...``) but it will
    automatically be converted to uppercase internally.
    """
    uriRegEx = re.compile(r"(?P<protocol>[Pp][Yy][Rr][Oo][a-zA-Z]*):(?P<object>\S+?)(@(?P<location>.+))?$")

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
            self._parseLocation(location, config.NS_PORT)
        elif self.protocol == "PYRO":
            if not location:
                raise errors.PyroError("invalid uri")
            self._parseLocation(location, None)
        elif self.protocol == "PYROMETA":
            self.object = set(m.strip() for m in self.object.split(","))
            self._parseLocation(location, config.NS_PORT)
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
                ipv6locationmatch = re.match(r"\[([0-9a-fA-F:%]+)](:(\d+))?", location)
                if not ipv6locationmatch:
                    raise errors.PyroError("invalid ipv6 address: the part between brackets must be a numeric ipv6 address")
                self.host, _, self.port = ipv6locationmatch.groups()
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
        if self.protocol == "PYROMETA":
            result = "PYROMETA:" + ",".join(self.object)
        else:
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
        return "<%s.%s at 0x%x; %s>" % (self.__class__.__module__, self.__class__.__name__, id(self), str(self))

    def __eq__(self, other):
        if not isinstance(other, URI):
            return False
        return (self.protocol, self.object, self.sockname, self.host, self.port) ==\
               (other.protocol, other.object, other.sockname, other.host, other.port)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.protocol, str(self.object), self.sockname, self.host, self.port))

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

    def __init__(self, send, name, max_retries):
        self.__send = send
        self.__name = name
        self.__max_retries = max_retries

    def __getattr__(self, name):
        return _RemoteMethod(self.__send, "%s.%s" % (self.__name, name), self.__max_retries)

    def __call__(self, *args, **kwargs):
        for attempt in range(self.__max_retries + 1):
            try:
                return self.__send(self.__name, args, kwargs)
            except (errors.ConnectionClosedError, errors.TimeoutError):
                # only retry for recoverable network errors
                if attempt >= self.__max_retries:
                    # last attempt, raise the exception
                    raise


class Proxy(object):
    """
    Pyro proxy for a remote object. Intercepts method calls and dispatches them to the remote object.

    .. automethod:: _pyroBind
    .. automethod:: _pyroRelease
    .. automethod:: _pyroReconnect
    .. automethod:: _pyroBatch
    .. automethod:: _pyroAsync
    .. automethod:: _pyroAnnotations
    .. automethod:: _pyroResponseAnnotations
    .. automethod:: _pyroValidateHandshake
    .. autoattribute:: _pyroTimeout
    .. autoattribute:: _pyroHmacKey
    .. attribute:: _pyroMaxRetries

        Number of retries to perform on communication calls by this proxy, allows you to override the default setting.

    .. attribute:: _pyroSerializer

        Name of the serializer to use by this proxy, allows you to override the default setting.

    .. attribute:: _pyroHandshake

        The data object that should be sent in the initial connection handshake message. Can be any serializable object.
    """
    __pyroAttributes = frozenset(
        ["__getnewargs__", "__getnewargs_ex__", "__getinitargs__", "_pyroConnection", "_pyroUri",
         "_pyroOneway", "_pyroMethods", "_pyroAttrs", "_pyroTimeout", "_pyroSeq", "_pyroHmacKey",
         "_pyroRawWireResponse", "_pyroHandshake", "_pyroMaxRetries", "_pyroSerializer", "_Proxy__async",
         "_Proxy__pyroHmacKey", "_Proxy__pyroTimeout", "_Proxy__pyroConnLock"])

    def __init__(self, uri, connected_socket=None):
        if connected_socket:
            uri = URI("PYRO:" + uri + "@<<connected-socket>>:0")
        if isinstance(uri, basestring):
            uri = URI(uri)
        elif not isinstance(uri, URI):
            raise TypeError("expected Pyro URI")
        self._pyroUri = uri
        self._pyroConnection = None
        self._pyroSerializer = None  # can be set to the name of a serializer to override the global one per-proxy
        self._pyroMethods = set()  # all methods of the remote object, gotten from meta-data
        self._pyroAttrs = set()  # attributes of the remote object, gotten from meta-data
        self._pyroOneway = set()  # oneway-methods of the remote object, gotten from meta-data
        self._pyroSeq = 0  # message sequence number
        self._pyroRawWireResponse = False  # internal switch to enable wire level responses
        self._pyroHandshake = "hello"  # the data object that should be sent in the initial connection handshake message
        self._pyroMaxRetries = config.MAX_RETRIES
        self.__pyroHmacKey = None
        self.__pyroTimeout = config.COMMTIMEOUT
        self.__pyroConnLock = threading.RLock()
        util.get_serializer(config.SERIALIZER)  # assert that the configured serializer is available
        self.__async = False
        current_context.annotations = {}
        current_context.response_annotations = {}
        if connected_socket:
            self.__pyroCreateConnection(False, connected_socket)

    @property
    def _pyroHmacKey(self):
        """the HMAC key (bytes) that this proxy uses"""
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
        if config.METADATA:
            # get metadata if it's not there yet
            if not self._pyroMethods and not self._pyroAttrs:
                self._pyroGetMetadata()
        if name in self._pyroAttrs:
            return self._pyroInvoke("__getattr__", (name,), None)
        if config.METADATA and name not in self._pyroMethods:
            # client side check if the requested attr actually exists
            raise AttributeError("remote object '%s' has no exposed attribute or method '%s'" % (self._pyroUri, name))
        if self.__async:
            return _AsyncRemoteMethod(self, name, self._pyroMaxRetries)
        return _RemoteMethod(self._pyroInvoke, name, self._pyroMaxRetries)

    def __setattr__(self, name, value):
        if name in Proxy.__pyroAttributes:
            return super(Proxy, self).__setattr__(name, value)  # one of the special pyro attributes
        if config.METADATA:
            # get metadata if it's not there yet
            if not self._pyroMethods and not self._pyroAttrs:
                self._pyroGetMetadata()
        if name in self._pyroAttrs:
            return self._pyroInvoke("__setattr__", (name, value), None)  # remote attribute
        if config.METADATA:
            # client side validation if the requested attr actually exists
            raise AttributeError("remote object '%s' has no exposed attribute '%s'" % (self._pyroUri, name))
        # metadata disabled, just treat it as a local attribute on the proxy:
        return super(Proxy, self).__setattr__(name, value)

    def __repr__(self):
        if self._pyroConnection:
            connected = "connected " + self._pyroConnection.family()
        else:
            connected = "not connected"
        return "<%s.%s at 0x%x; %s; for %s>" % (self.__class__.__module__, self.__class__.__name__,
                                                id(self), connected, self._pyroUri)

    def __unicode__(self):
        return str(self)

    def __getstate_for_dict__(self):
        encodedHmac = None
        if self._pyroHmacKey is not None:
            encodedHmac = "b64:" + (base64.b64encode(self._pyroHmacKey).decode("ascii"))
        # for backwards compatibility reasons we also put the timeout and maxretries into the state
        return self._pyroUri.asString(), tuple(self._pyroOneway), tuple(self._pyroMethods), tuple(self._pyroAttrs),\
            self.__pyroTimeout, encodedHmac, self._pyroHandshake, self._pyroMaxRetries, self._pyroSerializer

    def __setstate_from_dict__(self, state):
        uri = URI(state[0])
        oneway = set(state[1])
        methods = set(state[2])
        attrs = set(state[3])
        timeout = state[4]
        hmac_key = state[5]
        handshake = state[6]
        max_retries = state[7]
        serializer = None if len(state) < 9 else state[8]
        if hmac_key:
            if hmac_key.startswith("b64:"):
                hmac_key = base64.b64decode(hmac_key[4:].encode("ascii"))
            else:
                raise errors.ProtocolError("hmac encoding error")
        self.__setstate__((uri, oneway, methods, attrs, timeout, hmac_key, handshake, max_retries, serializer))

    def __getstate__(self):
        # for backwards compatibility reasons we also put the timeout and maxretries into the state
        return self._pyroUri, self._pyroOneway, self._pyroMethods, self._pyroAttrs, self.__pyroTimeout, \
            self._pyroHmacKey, self._pyroHandshake, self._pyroMaxRetries, self._pyroSerializer

    def __setstate__(self, state):
        # Note that the timeout and maxretries are also part of the state (for backwards compatibility reasons),
        # but we're not using them here. Instead we get the configured values from the 'local' config.
        self._pyroUri, self._pyroOneway, self._pyroMethods, self._pyroAttrs, _, self._pyroHmacKey, self._pyroHandshake = state[:7]
        self._pyroSerializer = None if len(state) < 9 else state[8]
        self.__pyroTimeout = config.COMMTIMEOUT
        self._pyroMaxRetries = config.MAX_RETRIES
        self._pyroConnection = None
        self._pyroSeq = 0
        self._pyroRawWireResponse = False
        self.__pyroConnLock = threading.RLock()
        self.__async = False

    def __copy__(self):
        uriCopy = URI(self._pyroUri)
        p = type(self)(uriCopy)
        p._pyroOneway = set(self._pyroOneway)
        p._pyroMethods = set(self._pyroMethods)
        p._pyroAttrs = set(self._pyroAttrs)
        p._pyroSerializer = self._pyroSerializer
        p._pyroTimeout = self._pyroTimeout
        p._pyroHandshake = self._pyroHandshake
        p._pyroHmacKey = self._pyroHmacKey
        p._pyroRawWireResponse = self._pyroRawWireResponse
        p._pyroMaxRetries = self._pyroMaxRetries
        p.__async = self.__async
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
                if self._pyroConnection.keep_open:
                    return
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

    _pyroTimeout = property(__pyroGetTimeout, __pyroSetTimeout, doc="""
        The timeout in seconds for calls on this proxy. Defaults to ``None``.
        If the timeout expires before the remote method call returns,
        Pyro will raise a :exc:`Pyro4.errors.TimeoutError`""")

    def _pyroInvoke(self, methodname, vargs, kwargs, flags=0, objectId=None):
        """perform the remote method call communication"""
        current_context.response_annotations = {}
        with self.__pyroConnLock:
            if self._pyroConnection is None:
                self.__pyroCreateConnection()
            serializer = util.get_serializer(self._pyroSerializer or config.SERIALIZER)
            objectId = objectId or self._pyroConnection.objectId
            annotations = self.__annotations()
            if vargs and isinstance(vargs[0], SerializedBlob):
                # special serialization of a 'blob' that stays serialized
                data, compressed, flags = self.__serializeBlobArgs(vargs, kwargs, annotations, flags, objectId, methodname, serializer)
            else:
                # normal serialization of the remote call
                data, compressed = serializer.serializeCall(objectId, methodname, vargs, kwargs, compress=config.COMPRESSION)
            if compressed:
                flags |= message.FLAGS_COMPRESSED
            if methodname in self._pyroOneway:
                flags |= message.FLAGS_ONEWAY
            self._pyroSeq = (self._pyroSeq + 1) & 0xffff
            msg = message.Message(message.MSG_INVOKE, data, serializer.serializer_id, flags, self._pyroSeq,
                                  annotations=annotations, hmac_key=self._pyroHmacKey)
            if config.LOGWIRE:
                _log_wiredata(log, "proxy wiredata sending", msg)
            try:
                self._pyroConnection.send(msg.to_bytes())
                del msg  # invite GC to collect the object, don't wait for out-of-scope
                if flags & message.FLAGS_ONEWAY:
                    return None  # oneway call, no response data
                else:
                    msg = message.Message.recv(self._pyroConnection, [message.MSG_RESULT], hmac_key=self._pyroHmacKey)
                    if config.LOGWIRE:
                        _log_wiredata(log, "proxy wiredata received", msg)
                    self.__pyroCheckSequence(msg.seq)
                    if msg.serializer_id != serializer.serializer_id:
                        error = "invalid serializer in response: %d" % msg.serializer_id
                        log.error(error)
                        raise errors.SerializeError(error)
                    if msg.annotations:
                        current_context.response_annotations = msg.annotations
                        self._pyroResponseAnnotations(msg.annotations, msg.type)
                    if self._pyroRawWireResponse:
                        msg.decompress_if_needed()
                        return msg
                    data = serializer.deserializeData(msg.data, compressed=msg.flags & message.FLAGS_COMPRESSED)
                    if msg.flags & message.FLAGS_ITEMSTREAMRESULT:
                        streamId = bytes(msg.annotations.get("STRM", b"")).decode()
                        if not streamId:
                            raise errors.ProtocolError("result of call is an iterator, but the server is not configured to allow streaming")
                        return _StreamResultIterator(streamId, self)
                    if msg.flags & message.FLAGS_EXCEPTION:
                        if sys.platform == "cli":
                            util.fixIronPythonExceptionForPickle(data, False)
                        raise data  # if you see this in your traceback, you should probably inspect the remote traceback as well
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

    def __pyroCreateConnection(self, replaceUri=False, connected_socket=None):
        """
        Connects this proxy to the remote Pyro daemon. Does connection handshake.
        Returns true if a new connection was made, false if an existing one was already present.
        """
        def connect_and_handshake(conn):
            try:
                if self._pyroConnection is not None:
                    return False  # already connected
                if config.SSL:
                    sslContext = socketutil.getSSLcontext(clientcert=config.SSL_CLIENTCERT,
                                                          clientkey=config.SSL_CLIENTKEY,
                                                          keypassword=config.SSL_CLIENTKEYPASSWD,
                                                          cacerts=config.SSL_CACERTS)
                else:
                    sslContext = None
                sock = socketutil.createSocket(connect=connect_location,
                                               reuseaddr=config.SOCK_REUSE,
                                               timeout=self.__pyroTimeout,
                                               nodelay=config.SOCK_NODELAY,
                                               sslContext=sslContext)
                conn = socketutil.SocketConnection(sock, uri.object)
                # Do handshake.
                serializer = util.get_serializer(self._pyroSerializer or config.SERIALIZER)
                data = {"handshake": self._pyroHandshake}
                if config.METADATA:
                    # the object id is only used/needed when piggybacking the metadata on the connection response
                    # make sure to pass the resolved object id instead of the logical id
                    data["object"] = uri.object
                    flags = message.FLAGS_META_ON_CONNECT
                else:
                    flags = 0
                data, compressed = serializer.serializeData(data, config.COMPRESSION)
                if compressed:
                    flags |= message.FLAGS_COMPRESSED
                msg = message.Message(message.MSG_CONNECT, data, serializer.serializer_id, flags, self._pyroSeq,
                                      annotations=self.__annotations(False), hmac_key=self._pyroHmacKey)
                if config.LOGWIRE:
                    _log_wiredata(log, "proxy connect sending", msg)
                conn.send(msg.to_bytes())
                msg = message.Message.recv(conn, [message.MSG_CONNECTOK, message.MSG_CONNECTFAIL], hmac_key=self._pyroHmacKey)
                if config.LOGWIRE:
                    _log_wiredata(log, "proxy connect response received", msg)
            except Exception as x:
                if conn:
                    conn.close()
                err = "cannot connect to %s: %s" % (connect_location, x)
                log.error(err)
                if isinstance(x, errors.CommunicationError):
                    raise
                else:
                    ce = errors.CommunicationError(err)
                    if sys.version_info >= (3, 0):
                        ce.__cause__ = x
                    raise ce
            else:
                handshake_response = "?"
                if msg.data:
                    serializer = util.get_serializer_by_id(msg.serializer_id)
                    handshake_response = serializer.deserializeData(msg.data, compressed=msg.flags & message.FLAGS_COMPRESSED)
                if msg.type == message.MSG_CONNECTFAIL:
                    if sys.version_info < (3, 0):
                        error = "connection to %s rejected: %s" % (connect_location, handshake_response.decode())
                    else:
                        error = "connection to %s rejected: %s" % (connect_location, handshake_response)
                    conn.close()
                    log.error(error)
                    raise errors.CommunicationError(error)
                elif msg.type == message.MSG_CONNECTOK:
                    if msg.flags & message.FLAGS_META_ON_CONNECT:
                        self.__processMetadata(handshake_response["meta"])
                        handshake_response = handshake_response["handshake"]
                    self._pyroConnection = conn
                    if replaceUri:
                        self._pyroUri = uri
                    self._pyroValidateHandshake(handshake_response)
                    log.debug("connected to %s - %s - %s", self._pyroUri, conn.family(), "SSL" if sslContext else "unencrypted")
                    if msg.annotations:
                        self._pyroResponseAnnotations(msg.annotations, msg.type)
                else:
                    conn.close()
                    err = "cannot connect to %s: invalid msg type %d received" % (connect_location, msg.type)
                    log.error(err)
                    raise errors.ProtocolError(err)

        with self.__pyroConnLock:
            if self._pyroConnection is not None:
                return False  # already connected
            if connected_socket:
                if config.SSL and not isinstance(connected_socket, ssl.SSLSocket):
                    raise socket.error("SSL configured for Pyro but existing socket is not a SSL socket")
                uri = self._pyroUri
            else:
                uri = _resolve(self._pyroUri, self._pyroHmacKey)
            # socket connection (normal or Unix domain socket)
            conn = None
            log.debug("connecting to %s", uri)
            connect_location = uri.sockname or (uri.host, uri.port)
            if connected_socket:
                self._pyroConnection = socketutil.SocketConnection(connected_socket, uri.object, True)
            else:
                connect_and_handshake(conn)
            if config.METADATA:
                # obtain metadata if this feature is enabled, and the metadata is not known yet
                if self._pyroMethods or self._pyroAttrs:
                    log.debug("reusing existing metadata")
                else:
                    self._pyroGetMetadata(uri.object)
            return True

    def _pyroGetMetadata(self, objectId=None, known_metadata=None):
        """
        Get metadata from server (methods, attrs, oneway, ...) and remember them in some attributes of the proxy.
        Usually this will already be known due to the default behavior of the connect handshake, where the
        connect response also includes the metadata.
        """
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
            self.__processMetadata(result)
        except errors.PyroError:
            log.exception("problem getting metadata")
            raise

    def __processMetadata(self, metadata):
        if not metadata:
            return
        self._pyroOneway = set(metadata["oneway"])
        self._pyroMethods = set(metadata["methods"])
        self._pyroAttrs = set(metadata["attrs"])
        if log.isEnabledFor(logging.DEBUG):
            log.debug("from meta: methods=%s, oneway methods=%s, attributes=%s",
                      sorted(self._pyroMethods), sorted(self._pyroOneway), sorted(self._pyroAttrs))
        if not self._pyroMethods and not self._pyroAttrs:
            raise errors.PyroError("remote object doesn't expose any methods or attributes. Did you forget setting @expose on them?")

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

    def _pyroAsync(self, asynchronous=True):
        """turns the proxy into asynchronous mode so you can do asynchronous method calls,
        or sets it back to normal sync mode if you set asynchronous=False.
        This setting is strictly on a per-proxy basis (unless an exact clone is made
        via copy.copy)."""
        self.__async = asynchronous

    if sys.version_info < (3, 7):
        # async keyword backwards compatibility
        _pyroAsync_37 = _pyroAsync

        def _pyroAsync(self, asynchronous=True, **kwargs):
            if kwargs:
                kword = list(kwargs.keys())
                if kword != ["async"]:
                    raise TypeError("_pyroAsync() got an unexpected keyword argument '{:s}'".format(kword[0]))
                asynchronous = kwargs["async"]
            return Proxy._pyroAsync_37(self, asynchronous)

    def _pyroInvokeBatch(self, calls, oneway=False):
        flags = message.FLAGS_BATCH
        if oneway:
            flags |= message.FLAGS_ONEWAY
        return self._pyroInvoke("<batch>", calls, None, flags)

    def _pyroAnnotations(self):
        """
        Override to return a dict with custom user annotations to be sent with each request message.
        Code using Pyro 4.56 or newer can skip this and instead set the annotations directly on the context object.
        """
        return {}

    def _pyroResponseAnnotations(self, annotations, msgtype):
        """
        Process any response annotations (dictionary set by the daemon).
        Usually this contains the internal Pyro annotations such as hmac and correlation id,
        and if you override the annotations method in the daemon, can contain your own annotations as well.
        Code using Pyro 4.56 or newer can skip this and instead read the response_annotations directly from the context object.
        """
        pass

    def _pyroValidateHandshake(self, response):
        """
        Process and validate the initial connection handshake response data received from the daemon.
        Simply return without error if everything is ok.
        Raise an exception if something is wrong and the connection should not be made.
        """
        return

    def __annotations(self, clear=True):
        annotations = current_context.annotations
        if current_context.correlation_id:
            annotations["CORR"] = current_context.correlation_id.bytes
        else:
            annotations.pop("CORR", None)
        annotations.update(self._pyroAnnotations())
        if clear:
            current_context.annotations = {}
        return annotations

    def __serializeBlobArgs(self, vargs, kwargs, annotations, flags, objectId, methodname, serializer):
        """
        Special handling of a "blob" argument that has to stay serialized until explicitly deserialized in client code.
        This makes efficient, transparent gateways or dispatchers and such possible:
        they don't have to de/reserialize the message and are independent from the serialized class definitions.
        Annotations are passed in because some blob metadata is added. They're not part of the blob itself.
        """
        if len(vargs) > 1 or kwargs:
            raise errors.SerializeError("if SerializedBlob is used, it must be the only argument")
        blob = vargs[0]
        flags |= message.FLAGS_KEEPSERIALIZED
        # Pass the objectId and methodname separately in an annotation because currently,
        # they are embedded inside the serialized message data. And we're not deserializing that,
        # so we have to have another means of knowing the object and method it is meant for...
        # A better solution is perhaps to split the actual remote method arguments from the
        # control data (object + methodname) but that requires a major protocol change.
        # The code below is not as nice but it works without any protocol change and doesn't
        # require a hack either - so it's actually not bad like this.
        import marshal
        annotations["BLBI"] = marshal.dumps((blob.info, objectId, methodname))
        if blob._contains_blob:
            # directly pass through the already serialized msg data from within the blob
            protocol_msg = blob._data
            data, compressed = protocol_msg.data, protocol_msg.flags & message.FLAGS_COMPRESSED
        else:
            # replaces SerializedBlob argument with the data to be serialized
            data, compressed = serializer.serializeCall(objectId, methodname, blob._data, kwargs, compress=config.COMPRESSION)
        return data, compressed, flags


class _StreamResultIterator(object):
    """
    Pyro returns this as a result of a remote call which returns an iterator or generator.
    It is a normal iterable and produces elements on demand from the remote iterator.
    You can simply use it in for loops, list comprehensions etc.
    """
    def __init__(self, streamId, proxy):
        self.streamId = streamId
        self.proxy = proxy
        self.pyroseq = proxy._pyroSeq

    def __iter__(self):
        return self

    def next(self):
        # python 2.x support
        return self.__next__()

    def __next__(self):
        if self.proxy is None:
            raise StopIteration
        if self.proxy._pyroConnection is None:
            raise errors.ConnectionClosedError("the proxy for this stream result has been closed")
        self.pyroseq += 1
        try:
            return self.proxy._pyroInvoke("get_next_stream_item", [self.streamId], {}, objectId=constants.DAEMON_NAME)
        except (StopIteration, GeneratorExit):
            # when the iterator is exhausted, the proxy is removed to avoid unneeded close_stream calls later
            # (the server has closed its part of the stream by itself already)
            self.proxy = None
            raise

    def __del__(self):
        self.close()

    def close(self):
        if self.proxy and self.proxy._pyroConnection is not None:
            if self.pyroseq == self.proxy._pyroSeq:
                # we're still in sync, it's okay to use the same proxy to close this stream
                self.proxy._pyroInvoke("close_stream", [self.streamId], {},
                                       flags=message.FLAGS_ONEWAY, objectId=constants.DAEMON_NAME)
            else:
                # The proxy's sequence number has diverged.
                # One of the reasons this can happen is because this call is being done from python's GC where
                # it decides to gc old iterator objects *during a new call on the proxy*.
                # If we use the same proxy and do a call in between, the other call on the proxy will get an out of sync seq and crash!
                # We create a temporary second proxy to call close_stream on. This is inefficient, but avoids the problem.
                try:
                    with self.proxy.__copy__() as closingProxy:
                        closingProxy._pyroInvoke("close_stream", [self.streamId], {},
                                                 flags=message.FLAGS_ONEWAY, objectId=constants.DAEMON_NAME)
                except errors.CommunicationError:
                    pass
        self.proxy = None


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
        copy = type(self)(self.__proxy)
        copy.__calls = list(self.__calls)
        return copy

    def __resultsgenerator(self, results):
        for result in results:
            if isinstance(result, futures._ExceptionWrapper):
                result.raiseIt()  # re-raise the remote exception locally.
            else:
                yield result  # it is a regular result object, yield that and continue.

    def __call__(self, oneway=False, asynchronous=False):
        if oneway and asynchronous:
            raise errors.PyroError("async oneway calls make no sense")
        if asynchronous:
            return _AsyncRemoteMethod(self, "<asyncbatch>", self.__proxy._pyroMaxRetries)()
        else:
            results = self.__proxy._pyroInvokeBatch(self.__calls, oneway)
            self.__calls = []  # clear for re-use
            if not oneway:
                return self.__resultsgenerator(results)

    if sys.version_info < (3, 7):
        # async keyword backwards compatibility
        call_37 = __call__

        def __call__(self, oneway=False, **kwargs):
            if kwargs:
                kword = list(kwargs.keys())
                if kword != ["async"] and kword != ["asynchronous"]:
                    raise TypeError("__call__() got an unexpected keyword argument '{:s}'".format(kword[0]))
                if kword == ["async"]:
                    kwargs = {"asynchronous": kwargs["async"]}
            kwargs["oneway"] = oneway
            return _BatchProxyAdapter.call_37(self, **kwargs)

    def _pyroInvoke(self, name, args, kwargs):
        # ignore all parameters, we just need to execute the batch
        results = self.__proxy._pyroInvokeBatch(self.__calls)
        self.__calls = []  # clear for re-use
        return self.__resultsgenerator(results)


class _AsyncRemoteMethod(object):
    """asynchronous method call abstraction (call will run in a background thread)"""
    def __init__(self, proxy, name, max_retries):
        self.__proxy = proxy
        self.__name = name
        self.__max_retries = max_retries

    def __getattr__(self, name):
        return _AsyncRemoteMethod(self.__proxy, "%s.%s" % (self.__name, name), self.__max_retries)

    def __call__(self, *args, **kwargs):
        result = futures.FutureResult()
        thread = threading.Thread(target=self.__asynccall, args=(result, args, kwargs))
        thread.setDaemon(True)
        thread.start()
        return result

    def __asynccall(self, asyncresult, args, kwargs):
        for attempt in range(self.__max_retries + 1):
            try:
                # use a copy of the proxy otherwise calls would still be done in sequence,
                # and use contextmanager to close the proxy after we're done
                with self.__proxy.__copy__() as proxy:
                    delay = 0.1 + random.random() / 5
                    while not proxy._pyroConnection:
                        try:
                            proxy._pyroBind()
                        except errors.CommunicationError as x:
                            if "no free workers" not in str(x):
                                raise
                            time.sleep(delay)   # wait a bit until a worker might be available again
                            delay += 0.4 + random.random() / 2
                            if 0 < config.COMMTIMEOUT / 2 < delay:
                                raise
                    value = proxy._pyroInvoke(self.__name, args, kwargs)
                asyncresult.value = value
                return
            except (errors.ConnectionClosedError, errors.TimeoutError) as x:
                # only retry for recoverable network errors
                if attempt >= self.__max_retries:
                    # ignore any exceptions here, return them as part of the asynchronous result instead
                    asyncresult.value = futures._ExceptionWrapper(x)
                    return
            except Exception as x:
                # ignore any exceptions here, return them as part of the asynchronous result instead
                asyncresult.value = futures._ExceptionWrapper(x)
                return


def batch(proxy):
    """convenience method to get a batch proxy adapter"""
    return proxy._pyroBatch()


def asyncproxy(proxy, asynchronous=True):
    """convenience method to set proxy to asynchronous or sync mode."""
    proxy._pyroAsync(asynchronous)


def pyroObjectToAutoProxy(obj):
    """reduce function that automatically replaces Pyro objects by a Proxy"""
    if config.AUTOPROXY:
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
    Decorator to mark a method or class to be exposed for remote calls (relevant when REQUIRE_EXPOSE=True)
    You can apply it to a method or a class as a whole.
    If you need to change the default instance mode or instance creator, also use a @behavior decorator.
    """
    if inspect.isdatadescriptor(method_or_class):
        func = method_or_class.fget or method_or_class.fset or method_or_class.fdel
        if util.is_private_attribute(func.__name__):
            raise AttributeError("exposing private names (starting with _) is not allowed")
        func._pyroExposed = True
        return method_or_class
    attrname = getattr(method_or_class, "__name__", None)
    if not attrname:
        # we could be dealing with a descriptor (classmethod/staticmethod), this means the order of the decorators is wrong
        if inspect.ismethoddescriptor(method_or_class):
            attrname = method_or_class.__get__(None, dict).__name__
            raise AttributeError("using @expose on a classmethod/staticmethod must be done "
                                 "after @classmethod/@staticmethod. Method: " + attrname)
        else:
            raise AttributeError("@expose cannot determine what this is: " + repr(method_or_class))
    if util.is_private_attribute(attrname):
        raise AttributeError("exposing private names (starting with _) is not allowed")
    if inspect.isclass(method_or_class):
        clazz = method_or_class
        log.debug("exposing all members of %r", clazz)
        for name in clazz.__dict__:
            if util.is_private_attribute(name):
                continue
            thing = getattr(clazz, name)
            if inspect.isfunction(thing) or inspect.ismethoddescriptor(thing):
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
        clazz._pyroExposed = True
        return clazz
    method_or_class._pyroExposed = True
    return method_or_class


def behavior(instance_mode="session", instance_creator=None):
    """
    Decorator to specify the server behavior of your Pyro class.
    """
    def _behavior(clazz):
        if not inspect.isclass(clazz):
            raise TypeError("behavior decorator can only be used on a class")
        if instance_mode not in ("single", "session", "percall"):
            raise ValueError("invalid instance mode: " + instance_mode)
        if instance_creator and not callable(instance_creator):
            raise TypeError("instance_creator must be a callable")
        clazz._pyroInstancing = (instance_mode, instance_creator)
        return clazz
    if not isinstance(instance_mode, basestring):
        raise SyntaxError("behavior decorator is missing argument(s)")
    return _behavior


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

    def get_metadata(self, objectId, as_lists=False):
        """
        Get metadata for the given object (exposed methods, oneways, attributes).
        If you get an error in your proxy saying that 'DaemonObject' has no attribute 'get_metadata',
        you're probably connecting to an older Pyro version (4.26 or earlier).
        Either upgrade the Pyro version or set METADATA config item to False in your client code.
        """
        obj = self.daemon.objectsById.get(objectId)
        if obj is not None:
            metadata = util.get_exposed_members(obj, only_exposed=config.REQUIRE_EXPOSE, as_lists=as_lists)
            if config.REQUIRE_EXPOSE and not metadata["methods"] and not metadata["attrs"]:
                # Something seems wrong: nothing is remotely exposed.
                # Possibly because older code not using @expose is now running with a more recent Pyro version
                # where @expose is mandatory in the default configuration. Give a hint to the user.
                if not inspect.isclass(obj):
                    obj = type(obj)
                warnings.warn("Class %r doesn't expose any methods or attributes. Did you forget setting @expose on them?" % obj)
            return metadata
        else:
            log.debug("unknown object requested: %s", objectId)
            raise errors.DaemonError("unknown object")

    def get_next_stream_item(self, streamId):
        if streamId not in self.daemon.streaming_responses:
            raise errors.PyroError("item stream terminated")
        client, timestamp, linger_timestamp, stream = self.daemon.streaming_responses[streamId]
        if client is None:
            # reset client connection association (can be None if proxy disconnected)
            self.daemon.streaming_responses[streamId] = (current_context.client, timestamp, 0, stream)
        try:
            return next(stream)
        except Exception:
            # in case of error (or StopIteration!) the stream is removed
            del self.daemon.streaming_responses[streamId]
            raise

    def close_stream(self, streamId):
        if streamId in self.daemon.streaming_responses:
            del self.daemon.streaming_responses[streamId]


class Daemon(object):
    """
    Pyro daemon. Contains server side logic and dispatches incoming remote method calls
    to the appropriate objects.
    """

    def __init__(self, host=None, port=0, unixsocket=None, nathost=None, natport=None, interface=DaemonObject, connected_socket=None):
        if connected_socket:
            nathost = natport = None
        else:
            if host is None:
                host = config.HOST
            if nathost is None:
                nathost = config.NATHOST
            if natport is None and nathost is not None:
                natport = config.NATPORT
            if nathost and unixsocket:
                raise ValueError("cannot use nathost together with unixsocket")
            if (nathost is None) ^ (natport is None):
                raise ValueError("must provide natport with nathost")
        self.__mustshutdown = threading.Event()
        self.__mustshutdown.set()
        self.__loopstopped = threading.Event()
        self.__loopstopped.set()
        if connected_socket:
            from Pyro4.socketserver.existingconnectionserver import SocketServer_ExistingConnection
            self.transportServer = SocketServer_ExistingConnection()
            self.transportServer.init(self, connected_socket)
        else:
            if config.SERVERTYPE == "thread":
                from Pyro4.socketserver.threadpoolserver import SocketServer_Threadpool
                self.transportServer = SocketServer_Threadpool()
            elif config.SERVERTYPE == "multiplex":
                from Pyro4.socketserver.multiplexserver import SocketServer_Multiplex
                self.transportServer = SocketServer_Multiplex()
            else:
                raise errors.PyroError("invalid server type '%s'" % config.SERVERTYPE)
            self.transportServer.init(self, host, port, unixsocket)
        #: The location (str of the form ``host:portnumber``) on which the Daemon is listening
        self.locationStr = self.transportServer.locationStr
        log.debug("daemon created on %s - %s (pid %d)", self.locationStr, socketutil.family_str(self.transportServer.sock), os.getpid())
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
        # assert that the configured serializers are available, and remember their ids:
        self.__serializer_ids = {util.get_serializer(ser_name).serializer_id for ser_name in config.SERIALIZERS_ACCEPTED}
        log.debug("accepted serializers: %s" % config.SERIALIZERS_ACCEPTED)
        log.debug("pyro protocol version: %d  pickle version: %d" % (constants.PROTOCOL_VERSION, config.PICKLE_PROTOCOL_VERSION))
        self.__pyroHmacKey = None
        self._pyroInstances = {}   # pyro objects for instance_mode=single (singletons, just one per daemon)
        self.streaming_responses = {}   # stream_id -> (client, creation_timestamp, linger_timestamp, stream)
        self.housekeeper_lock = threading.Lock()
        self.create_single_instance_lock = threading.Lock()
        self.__mustshutdown.clear()

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
        """the server socket used by the daemon"""
        return self.transportServer.sock

    @property
    def sockets(self):
        """list of all sockets used by the daemon (server socket and all active client sockets)"""
        return self.transportServer.sockets

    @property
    def selector(self):
        """the multiplexing selector used, if using the multiplex server type"""
        return self.transportServer.selector

    @staticmethod
    def serveSimple(objects, host=None, port=0, daemon=None, ns=True, verbose=True):
        """
        Basic method to fire up a daemon (or supply one yourself).
        objects is a dict containing objects to register as keys, and
        their names (or None) as values. If ns is true they will be registered
        in the naming server as well, otherwise they just stay local.
        If you need to publish on a unix domain socket you can't use this shortcut method.
        See the documentation on 'publishing objects' (in chapter: Servers) for more details.
        """
        if daemon is None:
            daemon = Daemon(host, port)
        with daemon:
            if ns:
                ns = _locateNS()
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
        self.streaming_responses = {}
        time.sleep(0.02)
        self.__mustshutdown.set()
        if self.transportServer:
            self.transportServer.shutdown()
            time.sleep(0.02)
        self.close()
        self.__loopstopped.wait(timeout=5)  # use timeout to avoid deadlock situations

    @property
    def _shutting_down(self):
        return self.__mustshutdown.is_set()

    def _handshake(self, conn, denied_reason=None):
        """
        Perform connection handshake with new clients.
        Client sends a MSG_CONNECT message with a serialized data payload.
        If all is well, return with a CONNECT_OK message.
        The reason we're not doing this with a MSG_INVOKE method call on the daemon
        (like when retrieving the metadata) is because we need to force the clients
        to get past an initial connect handshake before letting them invoke any method.
        Return True for successful handshake, False if something was wrong.
        If a denied_reason is given, the handshake will fail with the given reason.
        """
        serializer_id = util.MarshalSerializer.serializer_id
        msg_seq = 0
        try:
            msg = message.Message.recv(conn, [message.MSG_CONNECT], hmac_key=self._pyroHmacKey)
            msg_seq = msg.seq
            if denied_reason:
                raise Exception(denied_reason)
            if config.LOGWIRE:
                _log_wiredata(log, "daemon handshake received", msg)
            if msg.serializer_id not in self.__serializer_ids:
                raise errors.SerializeError("message used serializer that is not accepted: %d" % msg.serializer_id)
            if "CORR" in msg.annotations:
                current_context.correlation_id = uuid.UUID(bytes=msg.annotations["CORR"])
            else:
                current_context.correlation_id = uuid.uuid4()
            serializer_id = msg.serializer_id
            serializer = util.get_serializer_by_id(serializer_id)
            data = serializer.deserializeData(msg.data, msg.flags & message.FLAGS_COMPRESSED)
            handshake_response = self.validateHandshake(conn, data["handshake"])
            if msg.flags & message.FLAGS_META_ON_CONNECT:
                # Usually this flag will be enabled, which results in including the object metadata
                # in the handshake response. This avoids a separate remote call to get_metadata.
                flags = message.FLAGS_META_ON_CONNECT
                handshake_response = {
                    "handshake": handshake_response,
                    "meta": self.objectsById[constants.DAEMON_NAME].get_metadata(data["object"], as_lists=True)
                }
            else:
                flags = 0
            data, compressed = serializer.serializeData(handshake_response, config.COMPRESSION)
            msgtype = message.MSG_CONNECTOK
            if compressed:
                flags |= message.FLAGS_COMPRESSED
        except errors.ConnectionClosedError:
            log.debug("handshake failed, connection closed early")
            return False
        except Exception as x:
            log.debug("handshake failed, reason:", exc_info=True)
            serializer = util.get_serializer_by_id(serializer_id)
            data, compressed = serializer.serializeData(str(x), False)
            msgtype = message.MSG_CONNECTFAIL
            flags = message.FLAGS_COMPRESSED if compressed else 0
        # We need a minimal amount of response data or the socket will remain blocked
        # on some systems... (messages smaller than 40 bytes)
        msg = message.Message(msgtype, data, serializer_id, flags, msg_seq, annotations=self.__annotations(), hmac_key=self._pyroHmacKey)
        if config.LOGWIRE:
            _log_wiredata(log, "daemon handshake response", msg)
        conn.send(msg.to_bytes())
        return msg.type == message.MSG_CONNECTOK

    def validateHandshake(self, conn, data):
        """
        Override this to create a connection validator for new client connections.
        It should return a response data object normally if the connection is okay,
        or should raise an exception if the connection should be denied.
        """
        return "hello"

    def clientDisconnect(self, conn):
        """
        Override this to handle a client disconnect.
        Conn is the SocketConnection object that was disconnected.
        """
        pass

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
        except errors.CommunicationError as x:
            # we couldn't even get data from the client, this is an immediate error
            # log.info("error receiving data from client %s: %s", conn.sock.getpeername(), x)
            raise x
        try:
            request_flags = msg.flags
            request_seq = msg.seq
            request_serializer_id = msg.serializer_id
            current_context.correlation_id = uuid.UUID(bytes=msg.annotations["CORR"]) if "CORR" in msg.annotations else uuid.uuid4()
            if config.LOGWIRE:
                _log_wiredata(log, "daemon wiredata received", msg)
            if msg.type == message.MSG_PING:
                # return same seq, but ignore any data (it's a ping, not an echo). Nothing is deserialized.
                msg = message.Message(message.MSG_PING, b"pong", msg.serializer_id, 0, msg.seq,
                                      annotations=self.__annotations(), hmac_key=self._pyroHmacKey)
                if config.LOGWIRE:
                    _log_wiredata(log, "daemon wiredata sending", msg)
                conn.send(msg.to_bytes())
                return
            if msg.serializer_id not in self.__serializer_ids:
                raise errors.SerializeError("message used serializer that is not accepted: %d" % msg.serializer_id)
            serializer = util.get_serializer_by_id(msg.serializer_id)
            if request_flags & message.FLAGS_KEEPSERIALIZED:
                # pass on the wire protocol message blob unchanged
                objId, method, vargs, kwargs = self.__deserializeBlobArgs(msg)
            else:
                # normal deserialization of remote call arguments
                objId, method, vargs, kwargs = serializer.deserializeCall(msg.data, compressed=msg.flags & message.FLAGS_COMPRESSED)
            current_context.client = conn
            try:
                current_context.client_sock_addr = conn.sock.getpeername()   # store, because on oneway calls, socket will be disconnected
            except socket.error:
                current_context.client_sock_addr = None   # sometimes getpeername() doesn't work...
            current_context.seq = msg.seq
            current_context.annotations = msg.annotations
            current_context.msg_flags = msg.flags
            current_context.serializer_id = msg.serializer_id
            del msg  # invite GC to collect the object, don't wait for out-of-scope
            obj = self.objectsById.get(objId)
            if obj is not None:
                if inspect.isclass(obj):
                    obj = self._getInstance(obj, conn)
                if request_flags & message.FLAGS_BATCH:
                    # batched method calls, loop over them all and collect all results
                    data = []
                    for method, vargs, kwargs in vargs:
                        method = util.getAttribute(obj, method)
                        try:
                            result = method(*vargs, **kwargs)  # this is the actual method call to the Pyro object
                        except Exception:
                            xt, xv = sys.exc_info()[0:2]
                            log.debug("Exception occurred while handling batched request: %s", xv)
                            xv._pyroTraceback = util.formatTraceback(detailed=config.DETAILED_TRACEBACK)
                            if sys.platform == "cli":
                                util.fixIronPythonExceptionForPickle(xv, True)  # piggyback attributes
                            data.append(futures._ExceptionWrapper(xv))
                            break  # stop processing the rest of the batch
                        else:
                            data.append(result)    # note that we don't support streaming results in batch mode
                    wasBatched = True
                else:
                    # normal single method call
                    if method == "__getattr__":
                        # special case for direct attribute access (only exposed @properties are accessible)
                        data = util.get_exposed_property_value(obj, vargs[0], only_exposed=config.REQUIRE_EXPOSE)
                    elif method == "__setattr__":
                        # special case for direct attribute access (only exposed @properties are accessible)
                        data = util.set_exposed_property_value(obj, vargs[0], vargs[1], only_exposed=config.REQUIRE_EXPOSE)
                    else:
                        method = util.getAttribute(obj, method)
                        if request_flags & message.FLAGS_ONEWAY and config.ONEWAY_THREADED:
                            # oneway call to be run inside its own thread
                            _OnewayCallThread(target=method, args=vargs, kwargs=kwargs).start()
                        else:
                            isCallback = getattr(method, "_pyroCallback", False)
                            data = method(*vargs, **kwargs)  # this is the actual method call to the Pyro object
                            if not request_flags & message.FLAGS_ONEWAY:
                                isStream, data = self._streamResponse(data, conn)
                                if isStream:
                                    # throw an exception as well as setting message flags
                                    # this way, it is backwards compatible with older pyro versions.
                                    exc = errors.ProtocolError("result of call is an iterator")
                                    ann = {"STRM": data.encode()} if data else {}
                                    self._sendExceptionResponse(conn, request_seq, serializer.serializer_id, exc, None,
                                                                annotations=ann, flags=message.FLAGS_ITEMSTREAMRESULT)
                                    return
            else:
                log.debug("unknown object requested: %s", objId)
                raise errors.DaemonError("unknown object")
            if request_flags & message.FLAGS_ONEWAY:
                return  # oneway call, don't send a response
            else:
                data, compressed = serializer.serializeData(data, compress=config.COMPRESSION)
                response_flags = 0
                if compressed:
                    response_flags |= message.FLAGS_COMPRESSED
                if wasBatched:
                    response_flags |= message.FLAGS_BATCH
                msg = message.Message(message.MSG_RESULT, data, serializer.serializer_id, response_flags, request_seq,
                                      annotations=self.__annotations(), hmac_key=self._pyroHmacKey)
                current_context.response_annotations = {}
                if config.LOGWIRE:
                    _log_wiredata(log, "daemon wiredata sending", msg)
                conn.send(msg.to_bytes())
        except Exception:
            xt, xv = sys.exc_info()[0:2]
            msg = getattr(xv, "pyroMsg", None)
            if msg:
                request_seq = msg.seq
                request_serializer_id = msg.serializer_id
            if xt is not errors.ConnectionClosedError:
                if xt not in (StopIteration, GeneratorExit):
                    log.debug("Exception occurred while handling request: %r", xv)
                if not request_flags & message.FLAGS_ONEWAY:
                    if isinstance(xv, errors.SerializeError) or not isinstance(xv, errors.CommunicationError):
                        # only return the error to the client if it wasn't a oneway call, and not a communication error
                        # (in these cases, it makes no sense to try to report the error back to the client...)
                        tblines = util.formatTraceback(detailed=config.DETAILED_TRACEBACK)
                        self._sendExceptionResponse(conn, request_seq, request_serializer_id, xv, tblines)
            if isCallback or isinstance(xv, (errors.CommunicationError, errors.SecurityError)):
                raise  # re-raise if flagged as callback, communication or security error.

    def _clientDisconnect(self, conn):
        if config.ITER_STREAM_LINGER > 0:
            # client goes away, keep streams around for a bit longer (allow reconnect)
            for streamId in list(self.streaming_responses):
                info = self.streaming_responses.get(streamId, None)
                if info and info[0] is conn:
                    _, timestamp, _, stream = info
                    self.streaming_responses[streamId] = (None, timestamp, time.time(), stream)
        else:
            # client goes away, close any streams it had open as well
            for streamId in list(self.streaming_responses):
                info = self.streaming_responses.get(streamId, None)
                if info and info[0] is conn:
                    del self.streaming_responses[streamId]
        self.clientDisconnect(conn)  # user overridable hook

    def _housekeeping(self):
        """
        Perform periodical housekeeping actions (cleanups etc)
        """
        if self._shutting_down:
            return
        with self.housekeeper_lock:
            if self.streaming_responses:
                if config.ITER_STREAM_LIFETIME > 0:
                    # cleanup iter streams that are past their lifetime
                    for streamId in list(self.streaming_responses.keys()):
                        info = self.streaming_responses.get(streamId, None)
                        if info:
                            last_use_period = time.time() - info[1]
                            if 0 < config.ITER_STREAM_LIFETIME < last_use_period:
                                del self.streaming_responses[streamId]
                if config.ITER_STREAM_LINGER > 0:
                    # cleanup iter streams that are past their linger time
                    for streamId in list(self.streaming_responses.keys()):
                        info = self.streaming_responses.get(streamId, None)
                        if info and info[2]:
                            linger_period = time.time() - info[2]
                            if linger_period > config.ITER_STREAM_LINGER:
                                del self.streaming_responses[streamId]
            self.housekeeping()

    def housekeeping(self):
        """
        Override this to add custom periodic housekeeping (cleanup) logic.
        This will be called every few seconds by the running daemon's request loop.
        """
        pass

    def _getInstance(self, clazz, conn):
        """
        Find or create a new instance of the class
        """
        def createInstance(clazz, creator):
            try:
                if creator:
                    obj = creator(clazz)
                    if isinstance(obj, clazz):
                        return obj
                    raise TypeError("instance creator returned object of different type")
                return clazz()
            except Exception:
                log.exception("could not create pyro object instance")
                raise
        instance_mode, instance_creator = clazz._pyroInstancing
        if instance_mode == "single":
            # create and use one singleton instance of this class (not a global singleton, just exactly one per daemon)
            with self.create_single_instance_lock:
                instance = self._pyroInstances.get(clazz)
                if not instance:
                    log.debug("instancemode %s: creating new pyro object for %s", instance_mode, clazz)
                    instance = createInstance(clazz, instance_creator)
                    self._pyroInstances[clazz] = instance
                return instance
        elif instance_mode == "session":
            # Create and use one instance for this proxy connection
            # the instances are kept on the connection object.
            # (this is the default instance mode when using new style @expose)
            instance = conn.pyroInstances.get(clazz)
            if not instance:
                log.debug("instancemode %s: creating new pyro object for %s", instance_mode, clazz)
                instance = createInstance(clazz, instance_creator)
                conn.pyroInstances[clazz] = instance
            return instance
        elif instance_mode == "percall":
            # create and use a new instance just for this call
            log.debug("instancemode %s: creating new pyro object for %s", instance_mode, clazz)
            return createInstance(clazz, instance_creator)
        else:
            raise errors.DaemonError("invalid instancemode in registered class")

    def _sendExceptionResponse(self, connection, seq, serializer_id, exc_value, tbinfo, flags=0, annotations=None):
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
        flags |= message.FLAGS_EXCEPTION
        if compressed:
            flags |= message.FLAGS_COMPRESSED
        annotations = dict(annotations or {})
        annotations.update(self.annotations())
        msg = message.Message(message.MSG_RESULT, data, serializer.serializer_id, flags, seq,
                              annotations=annotations, hmac_key=self._pyroHmacKey)
        if config.LOGWIRE:
            _log_wiredata(log, "daemon wiredata sending (error response)", msg)
        connection.send(msg.to_bytes())

    def register(self, obj_or_class, objectId=None, force=False):
        """
        Register a Pyro object under the given id. Note that this object is now only
        known inside this daemon, it is not automatically available in a name server.
        This method returns a URI for the registered object.
        Pyro checks if an object is already registered, unless you set force=True.
        You can register a class or an object (instance) directly.
        For a class, Pyro will create instances of it to handle the remote calls according
        to the instance_mode (set via @expose on the class). The default there is one object
        per session (=proxy connection). If you register an object directly, Pyro will use
        that single object for *all* remote calls.
        """
        if objectId:
            if not isinstance(objectId, basestring):
                raise TypeError("objectId must be a string or None")
        else:
            objectId = "obj_" + uuid.uuid4().hex  # generate a new objectId
        if inspect.isclass(obj_or_class):
            if not hasattr(obj_or_class, "_pyroInstancing"):
                obj_or_class._pyroInstancing = ("session", None)
        if not force:
            if hasattr(obj_or_class, "_pyroId") and obj_or_class._pyroId != "":  # check for empty string is needed for Cython
                raise errors.DaemonError("object or class already has a Pyro id")
            if objectId in self.objectsById:
                raise errors.DaemonError("an object or class is already registered with that id")
        # set some pyro attributes
        obj_or_class._pyroId = objectId
        obj_or_class._pyroDaemon = self
        if config.AUTOPROXY:
            # register a custom serializer for the type to automatically return proxies
            # we need to do this for all known serializers
            for ser in util._serializers.values():
                if inspect.isclass(obj_or_class):
                    ser.register_type_replacement(obj_or_class, pyroObjectToAutoProxy)
                else:
                    ser.register_type_replacement(type(obj_or_class), pyroObjectToAutoProxy)
        # register the object/class in the mapping
        self.objectsById[obj_or_class._pyroId] = obj_or_class
        return self.uriFor(objectId)

    def unregister(self, objectOrId):
        """
        Remove a class or object from the known objects inside this daemon.
        You can unregister the class/object directly, or with its id.
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

    def resetMetadataCache(self, objectOrId, nat=True):
        """Reset cache of metadata when a Daemon has available methods/attributes
        dynamically updated.  Clients will have to get a new proxy to see changes"""
        uri = self.uriFor(objectOrId, nat)
        # can only be cached if registered, else no-op
        if uri.object in self.objectsById:
            registered_object = self.objectsById[uri.object]
            # Clear cache regardless of how it is accessed
            util.reset_exposed_members(registered_object, config.REQUIRE_EXPOSE, as_lists=True)
            util.reset_exposed_members(registered_object, config.REQUIRE_EXPOSE, as_lists=False)

    def proxyFor(self, objectOrId, nat=True):
        """
        Get a fully initialized Pyro Proxy for the given object (or object id) for this daemon.
        If nat is False, the configured NAT address (if any) is ignored.
        The object or id must be registered in this daemon, or you'll get an exception.
        (you can't get a proxy for an unknown object)
        """
        uri = self.uriFor(objectOrId, nat)
        proxy = Proxy(uri)
        try:
            registered_object = self.objectsById[uri.object]
        except KeyError:
            raise errors.DaemonError("object isn't registered in this daemon")
        meta = util.get_exposed_members(registered_object, only_exposed=config.REQUIRE_EXPOSE)
        proxy._pyroGetMetadata(known_metadata=meta)
        return proxy

    def close(self):
        """Close down the server and release resources"""
        self.__mustshutdown.set()
        self.streaming_responses = {}
        if self.transportServer:
            log.debug("daemon closing")
            self.transportServer.close()
            self.transportServer = None

    def annotations(self):
        """Override to return a dict with custom user annotations to be sent with each response message."""
        return {}

    def combine(self, daemon):
        """
        Combines the event loop of the other daemon in the current daemon's loop.
        You can then simply run the current daemon's requestLoop to serve both daemons.
        This works fine on the multiplex server type, but doesn't work with the threaded server type.
        """
        log.debug("combining event loop with other daemon")
        self.transportServer.combine_loop(daemon.transportServer)

    def __annotations(self):
        annotations = current_context.response_annotations
        if current_context.correlation_id:
            annotations["CORR"] = current_context.correlation_id.bytes
        else:
            annotations.pop("CORR", None)
        annotations.update(self.annotations())
        return annotations

    def __repr__(self):
        if hasattr(self, "locationStr"):
            family = socketutil.family_str(self.sock)
            return "<%s.%s at 0x%x; %s - %s; %d objects>" % (self.__class__.__module__, self.__class__.__name__,
                                                             id(self), self.locationStr, family, len(self.objectsById))
        else:
            # daemon objects may come back from serialized form without being properly initialized (by design)
            return "<%s.%s at 0x%x; unusable>" % (self.__class__.__module__, self.__class__.__name__, id(self))

    def __enter__(self):
        if not self.transportServer:
            raise errors.PyroError("cannot reuse this object")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __getstate__(self):
        # A little hack to make it possible to serialize Pyro objects, because they can reference a daemon,
        # but it is not meant to be able to properly serialize/deserialize Daemon objects.
        return {}

    def __getstate_for_dict__(self):
        return tuple(self.__getstate__())

    def __setstate_from_dict__(self, state):
        pass

    if sys.version_info < (3, 0):
        __lazy_dict_iterator_types = (type({}.iterkeys()), type({}.itervalues()), type({}.iteritems()))
    else:
        __lazy_dict_iterator_types = (type({}.keys()), type({}.values()), type({}.items()))

    def _streamResponse(self, data, client):
        if sys.version_info < (3, 4):
            from collections import Iterator
        else:
            from collections.abc import Iterator
        if isinstance(data, Iterator) or inspect.isgenerator(data):
            if config.ITER_STREAMING:
                if type(data) in self.__lazy_dict_iterator_types:
                    raise errors.PyroError("won't serialize or stream lazy dict iterators, convert to list yourself")
                stream_id = str(uuid.uuid4())
                self.streaming_responses[stream_id] = (client, time.time(), 0, data)
                return True, stream_id
            return True, None
        return False, data

    def __deserializeBlobArgs(self, protocolmsg):
        import marshal
        blobinfo = protocolmsg.annotations["BLBI"]
        if sys.platform == "cli" and type(blobinfo) is not str:
            # Ironpython's marshal expects str...
            blobinfo = str(blobinfo)
        blobinfo, objId, method = marshal.loads(blobinfo)
        blob = SerializedBlob(blobinfo, protocolmsg, is_blob=True)
        return objId, method, (blob,), {}  # object, method, vargs, kwargs


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
    serpent.register_class(futures._ExceptionWrapper, pyro_class_serpent_serializer)
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
util.SerializerBase.register_class_to_dict(futures._ExceptionWrapper, futures._ExceptionWrapper.__serialized_dict__, serpent_too=False)


def _log_wiredata(logger, text, msg):
    """logs all the given properties of the wire message in the given logger"""
    corr = str(uuid.UUID(bytes=msg.annotations["CORR"])) if "CORR" in msg.annotations else "?"
    logger.debug("%s: msgtype=%d flags=0x%x ser=%d seq=%d corr=%s\nannotations=%r\ndata=%r" %
                 (text, msg.type, msg.flags, msg.serializer_id, msg.seq, corr, msg.annotations, msg.data))


class _CallContext(threading.local):
    def __init__(self):
        # per-thread initialization
        self.client = None
        self.client_sock_addr = None
        self.seq = 0
        self.msg_flags = 0
        self.serializer_id = 0
        self.annotations = {}
        self.response_annotations = {}
        self.correlation_id = None

    def to_global(self):
        if sys.platform != "cli":
            return dict(self.__dict__)
        # ironpython somehow has problems getting at the values, so do it manually:
        return {
            "client": self.client,
            "seq": self.seq,
            "msg_flags": self.msg_flags,
            "serializer_id": self.serializer_id,
            "annotations": self.annotations,
            "response_annotations": self.response_annotations,
            "correlation_id": self.correlation_id,
            "client_sock_addr": self.client_sock_addr
        }

    def from_global(self, values):
        self.client = values["client"]
        self.seq = values["seq"]
        self.msg_flags = values["msg_flags"]
        self.serializer_id = values["serializer_id"]
        self.annotations = values["annotations"]
        self.response_annotations = values["response_annotations"]
        self.correlation_id = values["correlation_id"]
        self.client_sock_addr = values["client_sock_addr"]

    def track_resource(self, resource):
        """keep a weak reference to the resource to be tracked for this connection"""
        if self.client:
            self.client.tracked_resources.add(resource)
        else:
            raise errors.PyroError("cannot track resource on a connectionless call")

    def untrack_resource(self, resource):
        """no longer track the resource for this connection"""
        if self.client:
            self.client.tracked_resources.discard(resource)
        else:
            raise errors.PyroError("cannot untrack resource on a connectionless call")


class _OnewayCallThread(threading.Thread):
    def __init__(self, target, args, kwargs):
        super(_OnewayCallThread, self).__init__(target=target, args=args, kwargs=kwargs, name="oneway-call")
        self.daemon = True
        self.parent_context = current_context.to_global()

    def run(self):
        current_context.from_global(self.parent_context)
        super(_OnewayCallThread, self).run()


# name server utility function, here to avoid cyclic dependencies
def _resolve(uri, hmac_key=None):
    """
    Resolve a 'magic' uri (PYRONAME, PYROMETA) into the direct PYRO uri.
    It finds a name server, and use that to resolve a PYRONAME uri into the direct PYRO uri pointing to the named object.
    If uri is already a PYRO uri, it is returned unmodified.
    You can consider this a shortcut function so that you don't have to locate and use a name server proxy yourself.
    Note: if you need to resolve more than a few names, consider using the name server directly instead of repeatedly
    calling this function, to avoid the name server lookup overhead from each call.
    """
    if isinstance(uri, basestring):
        uri = URI(uri)
    elif not isinstance(uri, URI):
        raise TypeError("can only resolve Pyro URIs")
    if uri.protocol == "PYRO":
        return uri
    log.debug("resolving %s", uri)
    if uri.protocol == "PYRONAME":
        with _locateNS(uri.host, uri.port, hmac_key=hmac_key) as nameserver:
            return nameserver.lookup(uri.object)
    elif uri.protocol == "PYROMETA":
        with _locateNS(uri.host, uri.port, hmac_key=hmac_key) as nameserver:
            candidates = nameserver.list(metadata_all=uri.object)
            if candidates:
                candidate = random.choice(list(candidates.values()))
                log.debug("resolved to candidate %s", candidate)
                return URI(candidate)
            raise errors.NamingError("no registrations available with desired metadata properties %s" % uri.object)
    else:
        raise errors.PyroError("invalid uri protocol")


# name server utility function, here to avoid cyclic dependencies
def _locateNS(host=None, port=None, broadcast=True, hmac_key=None):
    """Get a proxy for a name server somewhere in the network."""
    if host is None:
        # first try localhost if we have a good chance of finding it there
        if config.NS_HOST in ("localhost", "::1") or config.NS_HOST.startswith("127."):
            if ":" in config.NS_HOST:  # ipv6
                hosts = ["[%s]" % config.NS_HOST]
            else:
                # Some systems (Debian Linux) have 127.0.1.1 in the hosts file assigned to the hostname,
                # try this too for convenience sake (only if it's actually used as a valid ip address)
                try:
                    socket.gethostbyaddr("127.0.1.1")
                    hosts = [config.NS_HOST] if config.NS_HOST == "127.0.1.1" else [config.NS_HOST, "127.0.1.1"]
                except socket.error:
                    hosts = [config.NS_HOST]
            for host in hosts:
                uristring = "PYRO:%s@%s:%d" % (constants.NAMESERVER_NAME, host, port or config.NS_PORT)
                log.debug("locating the NS: %s", uristring)
                proxy = Proxy(uristring)
                proxy._pyroHmacKey = hmac_key
                try:
                    proxy._pyroBind()
                    log.debug("located NS")
                    return proxy
                except errors.PyroError:
                    pass
        if config.PREFER_IP_VERSION == 6:
            broadcast = False   # ipv6 doesn't have broadcast. We should probably use multicast....
        if broadcast:
            # broadcast lookup
            if not port:
                port = config.NS_BCPORT
            log.debug("broadcast locate")
            sock = socketutil.createBroadcastSocket(reuseaddr=config.SOCK_REUSE, timeout=0.7)
            for _ in range(3):
                try:
                    for bcaddr in config.parseAddressesString(config.BROADCAST_ADDRS):
                        try:
                            sock.sendto(b"GET_NSURI", 0, (bcaddr, port))
                        except socket.error as x:
                            err = getattr(x, "errno", x.args[0])
                            # handle some errno's that some platforms like to throw:
                            if err not in socketutil.ERRNO_EADDRNOTAVAIL and err not in socketutil.ERRNO_EADDRINUSE:
                                raise
                    data, _ = sock.recvfrom(100)
                    sock.close()
                    if sys.version_info >= (3, 0):
                        data = data.decode("iso-8859-1")
                    log.debug("located NS: %s", data)
                    proxy = Proxy(data)
                    proxy._pyroHmacKey = hmac_key
                    return proxy
                except socket.timeout:
                    continue
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except (OSError, socket.error):
                pass
            sock.close()
            log.debug("broadcast locate failed, try direct connection on NS_HOST")
        else:
            log.debug("skipping broadcast lookup")
        # broadcast failed or skipped, try PYRO directly on specific host
        host = config.NS_HOST
        port = config.NS_PORT
    # pyro direct lookup
    if not port:
        port = config.NS_PORT
    if URI.isUnixsockLocation(host):
        uristring = "PYRO:%s@%s" % (constants.NAMESERVER_NAME, host)
    else:
        # if not a unix socket, check for ipv6
        if ":" in host:
            host = "[%s]" % host
        uristring = "PYRO:%s@%s:%d" % (constants.NAMESERVER_NAME, host, port)
    uri = URI(uristring)
    log.debug("locating the NS: %s", uri)
    proxy = Proxy(uri)
    proxy._pyroHmacKey = hmac_key
    try:
        proxy._pyroBind()
        log.debug("located NS")
        return proxy
    except errors.PyroError as x:
        e = errors.NamingError("Failed to locate the nameserver")
        if sys.version_info >= (3, 0):
            e.__cause__ = x
        raise e


class SerializedBlob(object):
    """
    Used to wrap some data to make Pyro pass this object transparently (it keeps the serialized payload as-is)
    Only when you need to access the actual client data you can deserialize on demand.
    This makes efficient, transparent gateways or dispatchers and such possible:
    they don't have to de/reserialize the message and are independent from the serialized class definitions.
    You have to pass this as the only parameter to a remote method call for Pyro to understand it.
    Init arguments:
    ``info`` = some (small) descriptive data about the blob. Can be a simple id or name or guid. Must be marshallable.
    ``data`` = the actual client data payload that you want to transfer in the blob. Can be anything that you would
    otherwise have used as regular remote call arguments.
    """
    def __init__(self, info, data, is_blob=False):
        self.info = info
        self._data = data
        self._contains_blob = is_blob

    def deserialized(self):
        """Retrieves the client data stored in this blob. Deserializes the data automatically if required."""
        if self._contains_blob:
            protocol_msg = self._data
            serializer = util.get_serializer_by_id(protocol_msg.serializer_id)
            _, _, data, _ = serializer.deserializeData(protocol_msg.data, protocol_msg.flags & message.FLAGS_COMPRESSED)
            return data
        else:
            return self._data


# call context thread local

current_context = _CallContext()
"""the context object for the current call. (thread-local)"""


# 'async' keyword backwards compatibility for Python versions older than 3.7. New code should not use this!
if sys.version_info < (3, 7):
    def asyncproxy(proxy, asynchronous=True, **kwargs):
        """convenience method to set proxy to asynchronous or sync mode."""
        if kwargs:
            kword = list(kwargs.keys())
            if kword != ["async"]:
                raise TypeError("asyncproxy() got an unexpected keyword argument '{:s}'".format(kword[0]))
            asynchronous = kwargs["async"]
        proxy._pyroAsync(asynchronous)
    current_module = sys.modules[__name__]
    pyro4_module = __import__("Pyro4")
    current_module.__dict__["async"] = pyro4_module.__dict__["async"] = asyncproxy
