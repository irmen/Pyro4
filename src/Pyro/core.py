"""
Core logic (uri, daemon, proxy stuff).

Pyro - Python Remote Objects.  Copyright by Irmen de Jong.
irmen@razorvine.net - http://www.razorvine.net/python/Pyro
"""

from __future__ import with_statement
import re, struct, sys, time, os
import logging, uuid
import Pyro.config
import Pyro.socketutil
import Pyro.util
import Pyro.errors
from Pyro import threadutil

__all__=["URI", "Proxy", "Daemon"]

log=logging.getLogger("Pyro.core")

class URI(object):
    """Pyro object URI (universal resource identifier)
    PYRO uri format: PYRO:objectid@location
        where location is one of:
          hostname:port  (tcp/ip socket on given port)
          ./p:pipename   (named pipe on localhost)
          ./u:sockname   (unix domain socket on localhost)
    
    MAGIC URI format for simple name resolution using Name server:
      PYRONAME:objectname[@location]  (optional name server location, can also omit location port)
    """
    uriRegEx=re.compile(r"(?P<protocol>PYRO[A-Z]*):(?P<object>\S+?)(@(?P<location>\S+))?$")
    __slots__=("protocol","object","pipename","sockname","host","port","object")

    def __init__(self, uri):
        if isinstance(uri, URI):
            state=uri.__getstate__()
            self.__setstate__(state)
            return
        if not isinstance(uri, basestring):
            raise TypeError("uri parameter object is of wrong type")
        self.pipename=self.sockname=self.host=self.port=None
        match=self.uriRegEx.match(uri)
        if not match:
            raise Pyro.errors.PyroError("invalid uri")
        self.protocol=match.group("protocol")
        self.object=match.group("object")
        location=match.group("location")
        if self.protocol=="PYRONAME":
            self._parseLocation(location, Pyro.config.NS_PORT)
            return
        if self.protocol=="PYRO":
            if not location:
                raise Pyro.errors.PyroError("invalid uri")
            self._parseLocation(location, None)
        else:
            raise Pyro.errors.PyroError("invalid uri (protocol)")

    def _parseLocation(self,location,defaultPort):
        if not location:
            return
        if location.startswith("./p:"):
            self.pipename=location[4:]
            if (not self.pipename) or ':' in self.pipename or '/' in self.pipename:
                raise Pyro.errors.PyroError("invalid uri (location)")
        elif location.startswith("./u:"):
            self.sockname=location[4:]
            if (not self.sockname) or ':' in self.sockname or '/' in self.sockname:
                raise Pyro.errors.PyroError("invalid uri (location)")
        else:
            self.host,_,self.port=location.partition(":")
            if not self.port:
                self.port=defaultPort
            try:
                self.port=int(self.port)
            except (ValueError, TypeError):
                raise Pyro.errors.PyroError("invalid uri (port)")        
    @staticmethod
    def isPipeOrUnixsockLocation(location):
        return location.startswith("./p:") or location.startswith("./u:")
    @property
    def location(self):
        if self.host:
            return "%s:%d" % (self.host, self.port)
        elif self.sockname:
            return "./u:"+self.sockname
        elif self.pipename:
            return "./p:"+self.pipename
        else:
            return None
    def asString(self):
        result=self.protocol+":"+self.object
        location=self.location
        if location:
            result+="@"+location
        return result
    def __str__(self):
        return self.asString()
    def __eq__(self,other):
        return (self.protocol, self.object, self.pipename, self.sockname, self.host, self.port) \
                == (other.protocol, other.object, other.pipename, other.sockname, other.host, other.port)
    __hash__=object.__hash__
    # note: getstate/setstate are not needed if we use pickle protocol 2,
    # but this way it helps pickle to make the representation smaller by omitting all attribute names.
    def __getstate__(self):
        return (self.protocol, self.object, self.pipename, self.sockname, self.host, self.port)
    def __setstate__(self,state):
        self.protocol, self.object, self.pipename, self.sockname, self.host, self.port = state


class _RemoteMethod(object):
    """method call abstraction, adapted from Python's xmlrpclib, but without nested calls at the moment"""
    def __init__(self, send, name):
        self.__send = send
        self.__name = name
    def __getattr__(self, name):
        return _RemoteMethod(self.__send, "%s.%s" % (self.__name, name))
    def __call__(self, *args, **kwargs):
        return self.__send(self.__name, args, kwargs)


class Proxy(object):
    """Pyro proxy for a remote object. Intercepts method calls and dispatches them to the remote object."""
    _pyroSerializer=Pyro.util.Serializer()
    __pyroAttributes=frozenset(["__getnewargs__","__getinitargs__","_pyroConnection","_pyroUri","_pyroOneway","_pyroTimeout"])
    def __init__(self, uri):
        if isinstance(uri, basestring):
            uri=URI(uri)
        elif not isinstance(uri, URI):
            raise TypeError("expected Pyro URI")
        self._pyroUri=uri
        self._pyroConnection=None
        self._pyroOneway=set()
        self.__pyroTimeout=Pyro.config.COMMTIMEOUT
        self.__pyroLock=threadutil.Lock()
    def __del__(self):
        if hasattr(self,"_pyroConnection"):
            self._pyroRelease()
    def __getattr__(self, name):
        if name in Proxy.__pyroAttributes: 
            # allows it to be safely pickled
            raise AttributeError(name)
        return _RemoteMethod(self.__pyroInvoke, name)
    def __str__(self):
        return "<Pyro Proxy for "+str(self._pyroUri)+">"
    def __unicode__(self):
        return str(self)
    def __getstate__(self):
        return self._pyroUri,self._pyroOneway,self._pyroSerializer,self.__pyroTimeout    # skip the connection
    def __setstate__(self, state):
        self._pyroUri,self._pyroOneway,self._pyroSerializer,self.__pyroTimeout = state
        self._pyroConnection=None
        self.__pyroLock=threadutil.Lock()
    def __copy__(self):
        uriCopy=URI(self._pyroUri)
        return Proxy(uriCopy)
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self._pyroRelease()

    def _pyroRelease(self):
        """release the connection to the pyro daemon"""
        if self._pyroConnection:
            self._pyroConnection.close()
            self._pyroConnection=None
            log.debug("connection released")

    def _pyroBind(self):
        """Bind this proxy to the exact object from the uri. That means that the proxy's uri
        will be updated with a direct PYRO uri, if it isn't one yet."""
        self._pyroRelease()
        self.__pyroCreateConnection(True)

    def __pyroGetTimeout(self):
        return self.__pyroTimeout
    def __pyroSetTimeout(self, timeout):
        self.__pyroTimeout=timeout
        if self._pyroConnection:
            self._pyroConnection.timeout=timeout
    _pyroTimeout=property(__pyroGetTimeout, __pyroSetTimeout)

    def __pyroInvoke(self, methodname, vargs, kwargs):
        """perform the remote method call communication"""
        if not self._pyroConnection:
            # rebind here, don't do it from inside the invoke because deadlock will occur
            self.__pyroCreateConnection()
        data,compressed=self._pyroSerializer.serialize( 
            (self._pyroConnection.objectId,methodname,vargs,kwargs), compress=Pyro.config.COMPRESSION )
        flags=0
        if compressed:
            flags |= MessageFactory.FLAGS_COMPRESSED
        if methodname in self._pyroOneway:
            flags |= MessageFactory.FLAGS_ONEWAY
        with self.__pyroLock:
            data=MessageFactory.createMessage(MessageFactory.MSG_INVOKE, data, flags)
            try:
                self._pyroConnection.send(data)
                if flags & MessageFactory.FLAGS_ONEWAY:
                    return None    # oneway call, no response data
                else:
                    header=self._pyroConnection.recv(MessageFactory.HEADERSIZE)
                    msgType,flags,dataLen=MessageFactory.parseMessageHeader(header)
                    if msgType!=MessageFactory.MSG_RESULT:
                        err="invoke: invalid msg type %d received" % msgType
                        log.error(err)
                        raise Pyro.errors.ProtocolError(err)
                    data=self._pyroConnection.recv(dataLen)
                    data=self._pyroSerializer.deserialize(data, compressed=flags & MessageFactory.FLAGS_COMPRESSED)
                    if flags & MessageFactory.FLAGS_EXCEPTION:
                        raise data
                    else:
                        return data
            except Pyro.errors.CommunicationError:
                # Communication error during read. To avoid corrupt transfers, we close the connection.
                # Otherwise we might receive the previous reply as a result of a new methodcall! 
                self._pyroRelease()
                raise

    def __pyroCreateConnection(self, replaceUri=False):
        """Connects this proxy to the remote Pyro daemon. Does connection handshake."""
        # import Pyro.naming # don't import globally because of cyclic dependancy 
        uri=Pyro.naming.resolve(self._pyroUri)
        if uri.host and uri.port:
            # socket connection
            log.debug("connecting to %s",uri)
            conn=None
            try:
                with self.__pyroLock:
                    sock=Pyro.socketutil.createSocket(connect=(uri.host, uri.port), timeout=self.__pyroTimeout)
                    conn=Pyro.socketutil.SocketConnection(sock, uri.object)
                    if Pyro.config.CONNECTHANDSHAKE:
                        # handshake
                        data=MessageFactory.createMessage(MessageFactory.MSG_CONNECT, None, 0)
                        conn.send(data)
                        data=conn.recv(MessageFactory.HEADERSIZE)
                        msgType,flags,dataLen=MessageFactory.parseMessageHeader(data) #@UnusedVariable (pydev)
                        # any trailing data (dataLen>0) is an error message, if any
                    else:
                        msgType=MessageFactory.MSG_CONNECTOK
            except Exception,x:
                if conn:
                    conn.close()
                err="cannot connect: %s" % x
                log.error(err)
                if isinstance(x, Pyro.errors.CommunicationError):
                    raise
                else:
                    raise Pyro.errors.CommunicationError(err)
            else:
                if msgType==MessageFactory.MSG_CONNECTFAIL:
                    error="connection rejected"
                    if dataLen>0:
                        error+=", reason: "+conn.recv(dataLen)
                    conn.close()
                    log.error(error)
                    raise Pyro.errors.CommunicationError(error)
                elif msgType==MessageFactory.MSG_CONNECTOK:
                    self._pyroConnection=conn
                    if replaceUri:
                        log.debug("replacing uri with bound one")
                        self._pyroUri=uri
                    log.debug("connected to %s",self._pyroUri)
                else:
                    conn.close()
                    err="connect: invalid msg type %d received" % msgType
                    log.error(err)
                    raise Pyro.errors.ProtocolError(err)
        else:
            raise NotImplementedError("non-socket uri connections not yet implemented")

    def _pyroReconnect(self, tries=100000000):
        self._pyroRelease()
        while tries:
            try:
                self.__pyroCreateConnection()
                return
            except Pyro.errors.CommunicationError:
                tries-=1
                if tries:
                    time.sleep(2)
        msg="failed to reconnect"
        log.error(msg)
        raise Pyro.errors.ConnectionClosedError(msg)


class MessageFactory(object):
    """internal helper class to construct Pyro protocol messages"""
    headerFmt = '!4sHHHi'    # header (id, version, msgtype, flags, dataLen)
    HEADERSIZE=struct.calcsize(headerFmt)
    MSG_CONNECT      = 1
    MSG_CONNECTOK    = 2
    MSG_CONNECTFAIL  = 3
    MSG_INVOKE       = 4
    MSG_RESULT       = 5
    FLAGS_EXCEPTION  = 1<<0
    FLAGS_COMPRESSED = 1<<1
    FLAGS_ONEWAY     = 1<<2

    @classmethod
    def createMessage(cls, msgType, data, flags=0):
        """creates a message containing a header followed by the given data"""
        data=data or ""
        msg=struct.pack(cls.headerFmt, "PYRO", Pyro.constants.PROTOCOL_VERSION, msgType, flags, len(data))
        return msg+data

    @classmethod
    def parseMessageHeader(cls, headerData):
        """Parses a message header. Returns a tuple of messagetype, messageflags, datalength.""" 
        if not headerData or len(headerData)!=cls.HEADERSIZE:
            raise Pyro.errors.ProtocolError("header data size mismatch")
        tag,ver,msgType,flags,dataLen = struct.unpack(cls.headerFmt, headerData)
        if tag!="PYRO" or ver!=Pyro.constants.PROTOCOL_VERSION:
            raise Pyro.errors.ProtocolError("invalid data or unsupported protocol version")
        return msgType,flags,dataLen


class DaemonObject(object):
    """The part of the daemon that is exposed as a Pyro object."""
    def __init__(self, daemon):
        self.daemon=daemon
    def registered(self):
        return list(self.daemon.objectsById.keys()) 
    def ping(self):
        pass

from Pyro.socketserver.threadpoolserver import SocketServer as SocketServer_Threadpool
from Pyro.socketserver.selectserver import SocketServer as SocketServer_Select

class Daemon(object):
    """
    Pyro daemon. Contains server side logic and dispatches incoming remote method calls
    to the appropriate objects.
    """
    def __init__(self, host=None, port=0):
        if host is None:
            host=Pyro.config.HOST
        if Pyro.config.SERVERTYPE=="thread":
            self.transportServer=SocketServer_Threadpool(self, host, port, Pyro.config.COMMTIMEOUT)
        elif Pyro.config.SERVERTYPE=="select":
            self.transportServer=SocketServer_Select(self, host, port, Pyro.config.COMMTIMEOUT)
        else:
            raise Pyro.errors.PyroError("invalid server type '%s'" % Pyro.config.SERVERTYPE)
        self.locationStr=self.transportServer.locationStr
        log.debug("created daemon on %s", self.locationStr) 
        self.serializer=Pyro.util.Serializer()
        pyroObject=DaemonObject(self)
        pyroObject._pyroId=Pyro.constants.DAEMON_NAME
        self.objectsById={pyroObject._pyroId: pyroObject}
        self.__mustshutdown=False
        self.__loopstopped=threadutil.Event()
        self.__loopstopped.set()

    def fileno(self):
        return self.transportServer.fileno()
    @property
    def sock(self):
        return self.transportServer.sock

    def requestLoop(self, loopCondition=lambda:True):
        """
        Goes in a loop to service incoming requests, until someone breaks this
        or calls shutdown from another thread.
        """  
        self.__mustshutdown=False
        log.info("daemon %s entering requestloop", self.locationStr)
        try:
            self.__loopstopped.clear()
            condition=lambda: not self.__mustshutdown and loopCondition()
            self.transportServer.requestLoop(loopCondition=condition)
        finally:
            self.__loopstopped.set()
        log.debug("daemon exits requestloop")

    def handleRequests(self):
        return self.transportServer.handleRequests()

    def shutdown(self):
        """Cleanly terminate a deamon that is running in the requestloop. It must be running
        in a different thread, or this method will deadlock."""
        log.debug("daemon shutting down")
        self.__mustshutdown=True
        self.pingConnection()
        time.sleep(0.05)
        self.close()
        self.__loopstopped.wait()
        log.info("daemon %s shut down", self.locationStr)

    def pingConnection(self):
        """bit of a hack to trigger a blocking server to get out of the loop, useful at clean shutdowns"""
        self.transportServer.pingConnection()

    def handshake(self, conn):
        if not Pyro.config.CONNECTHANDSHAKE:
            return True
        """Perform connection handshake with new clients"""
        header=conn.recv(MessageFactory.HEADERSIZE)
        msgType,flags,dataLen=MessageFactory.parseMessageHeader(header) #@UnusedVariable (pydev)
        if msgType!=MessageFactory.MSG_CONNECT:
            err="expected MSG_CONNECT message, got %d" % msgType
            log.warn(err)
            raise Pyro.errors.ProtocolError(err)
        if dataLen>0:
            conn.recv(dataLen) # read away any trailing data (unused at the moment)
        msg=MessageFactory.createMessage(MessageFactory.MSG_CONNECTOK,None,0)
        conn.send(msg)
        return True

    def handleRequest(self, conn):
        """
        Handle incoming Pyro request. Catches any exception that may occur and
        wraps it in a reply to the calling side, as to not make this server side loop
        terminate due to exceptions caused by remote invocations.
        """
        flags=0
        try:
            header=conn.recv(MessageFactory.HEADERSIZE)
            msgType,flags,dataLen=MessageFactory.parseMessageHeader(header)
            if msgType!=MessageFactory.MSG_INVOKE:
                err="handlerequest: invalid msg type %d received" % msgType
                log.warn(err)
                raise Pyro.errors.ProtocolError(err)
            data=conn.recv(dataLen)
            objId, method, vargs, kwargs=self.serializer.deserialize(
                                           data,compressed=flags & MessageFactory.FLAGS_COMPRESSED)
            obj=self.objectsById.get(objId)
            if obj is not None:
                if kwargs and sys.version_info<(2,6,5) and os.name!="java":
                    # Python before 2.6.5 doesn't accept unicode keyword arguments
                    kwargs = dict((str(k),kwargs[k]) for k in kwargs)
                log.debug("calling %s.%s",obj.__class__.__name__,method)
                obj=Pyro.util.resolveDottedAttribute(obj,method,Pyro.config.DOTTEDNAMES)
                if flags & MessageFactory.FLAGS_ONEWAY and Pyro.config.ONEWAY_THREADED:
                    # oneway call to be run inside its own thread
                    thread=threadutil.Thread(target=obj, args=vargs, kwargs=kwargs)
                    thread.setDaemon(True)
                    thread.start()
                else:
                    data=obj(*vargs,**kwargs)   # this is the actual method call to the Pyro object
            else:
                log.debug("unknown object requested: %s",objId)
                raise Pyro.errors.DaemonError("unknown object")
            if flags & MessageFactory.FLAGS_ONEWAY:
                return   # oneway call, don't send a response
            else:
                data,compressed=self.serializer.serialize(data,compress=Pyro.config.COMPRESSION)
                flags=0
                if compressed:
                    flags |= MessageFactory.FLAGS_COMPRESSED
                msg=MessageFactory.createMessage(MessageFactory.MSG_RESULT, data, flags)
                del data
                conn.send(msg)
        except Pyro.errors.CommunicationError,x:
            # communication errors are not handled here (including TimeoutError)
            raise
        except Exception,x:
            # all other errors are caught
            log.debug("Exception occurred while handling request: %s",x)
            if not flags & MessageFactory.FLAGS_ONEWAY:
                # only return the error to the client if it wasn't a oneway call
                tblines=Pyro.util.formatTraceback(detailed=Pyro.config.DETAILED_TRACEBACK)
                self.sendExceptionResponse(conn, x, tblines)

    def sendExceptionResponse(self, connection, exc_value, tbinfo):
        """send an exception back including the local traceback info"""
        setattr(exc_value, Pyro.constants.TRACEBACK_ATTRIBUTE, tbinfo)
        data,_=self.serializer.serialize(exc_value)
        msg=MessageFactory.createMessage(MessageFactory.MSG_RESULT, data, MessageFactory.FLAGS_EXCEPTION)
        del data
        connection.send(msg)

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
        if hasattr(obj,"_pyroId"):
            raise Pyro.errors.DaemonError("object already has a Pyro id")
        if objectId in self.objectsById:
            raise Pyro.errors.DaemonError("object already registered")
        obj._pyroId=objectId
        obj._pyroDaemon=self
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
            objectId=getattr(objectOrId,"_pyroId",None)
            if objectId is None:
                raise Pyro.errors.DaemonError("object isn't registered")
        else:
            objectId=objectOrId
            objectOrId=None
        if objectId==Pyro.constants.DAEMON_NAME:
            return
        if objectId in self.objectsById:
            del self.objectsById[objectId]
            if objectOrId is not None:
                del objectOrId._pyroId
                del objectOrId._pyroDaemon

    def uriFor(self, objectOrId=None):
        """
        Get a URI for the given object (or object id) from this daemon.
        Only a daemon can hand out proper uris because the access location is
        contained in them.
        Note that unregistered objects cannot be given an uri, but unregistered
        object names can (it's just a string we're creating in that case)
        """
        if not isinstance(objectOrId, basestring):
            objectOrId=getattr(objectOrId,"_pyroId",None)
            if objectOrId is None:
                raise Pyro.errors.DaemonError("object isn't registered")
        return URI("PYRO:"+objectOrId+"@"+self.locationStr)

    def close(self):
        """Close down the server and release resources"""
        log.debug("daemon closing")
        self.__del__()

    def __del__(self):
        ts=getattr(self,"transportServer",None)
        if ts is not None:
            self.transportServer.close()
            self.transportServer=None
    def __str__(self):
        return "<Pyro Daemon on "+self.locationStr+">"
    def __enter__(self):
        if not self.transportServer:
            raise Pyro.errors.PyroError("cannot reuse this object")
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
