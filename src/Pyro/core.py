"""
Core Pyro logic (uri, daemon, proxy stuff).
"""

import re, struct, sys
import logging, uuid, threading
from Pyro.errors import *
import Pyro.config
import Pyro.socketutil
import Pyro.util

__all__=["PyroURI", "Proxy", "Daemon"]

log=logging.getLogger("Pyro.core")

class PyroURI(object):
    """Pyro object URI (universal resource identifier)
    PYRO uri format: PYRO:objectid@location
        where location is one of:
          hostname       (tcp/ip socket on default port)
          hostname:port  (tcp/ip socket on given port)
          ./p:pipename   (named pipe on localhost)
          ./u:sockname   (unix domain socket on localhost)
    
    MAGIC URI formats:
      PYRONAME:logicalobjectname[@location]  (optional name server location)
      PYROLOC:logicalobjectname@location
        where location is the same as above.
      (these are used to be resolved to a direct PYRO: uri).
    """
    uriRegEx=re.compile(r"(?P<protocol>PYRO|PYRONAME|PYROLOC):(?P<object>\S+?)(@(?P<location>\S+))?$")
    __slots__=("protocol","object","pipename","sockname","host","port","object")
    def __init__(self, uri):
        uri=str(uri)  # allow to pass an existing PyroURI object
        self.pipename=self.sockname=self.host=self.port=None
        m=self.uriRegEx.match(uri)
        if not m:
            raise NamingError("invalid uri")
        self.protocol=m.group("protocol")
        self.object=m.group("object")
        location=m.group("location")
        if self.protocol=="PYRONAME":
            self._parseLocation(location, Pyro.config.NS_PORT)
            return
        if self.protocol in ("PYRO","PYROLOC"):
            if not location:
                raise NamingError("invalid uri")
            self._parseLocation(location, Pyro.config.PORT)
        else:
            raise NamingError("invalid uri (protocol)")
    def _parseLocation(self,location,defaultPort):
        if not location:
            return
        if location.startswith("./p:"):
            self.pipename=location[4:]
            if not self.pipename:
                raise NamingError("invalid uri (location)")
        elif location.startswith("./u:"):
            self.sockname=location[4:]
            if not self.sockname:
                raise NamingError("invalid uri (location)")
        else:
            self.host,_,self.port=location.partition(":")
            if not self.port:
                self.port=defaultPort
            else:
                try:
                    self.port=int(self.port)
                except ValueError:
                    raise NamingError("invalid uri (port)")        
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
    def __str__(self):
        s=self.protocol+":"+self.object
        location=self.location
        if location:
            s+="@"+location
        return s
    def __repr__(self):
        return "<PyroURI '"+str(self)+"'>"
    def __eq__(self,other):
        return (self.protocol, self.object, self.pipename, self.sockname, self.host, self.port) \
                == (other.protocol, other.object, other.pipename, other.sockname, other.host, other.port)
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
    def __call__(self, *args, **kwargs):
        return self.__send(self.__name, args, kwargs)


class Proxy(object):
    """Pyro proxy for a remote object. Intercepts method calls and dispatches them to the remote object."""
    def __init__(self, uri):
        if isinstance(uri, basestring):
            uri=Pyro.core.PyroURI(uri)
        elif not isinstance(uri, Pyro.core.PyroURI):
            raise TypeError("expected Pyro URI")
        self._pyroUri=uri
        self._pyroConnection=None
        self._pyroSerializer=Pyro.util.Serializer()
    def __del__(self):
        if hasattr(self,"_pyroConnection"):
            self._pyroRelease()
    def __getattr__(self, name):
        if name in ("__getnewargs__","__getinitargs__","_pyroConnection","_pyroUri"):        # allows it to be safely pickled
            raise AttributeError(name)
        return _RemoteMethod(self._pyroInvoke, name)
    def __repr__(self):
        return "<Pyro Proxy for "+str(self._pyroUri)+">"
    def __str__(self):
        return repr(self)
    def __getstate__(self):
        return self._pyroUri,self._pyroSerializer    # skip the connection
    def __setstate__(self, state):
        self._pyroUri, self._pyroSerializer = state
        self._pyroConnection=None
    def __copy__(self):
        uriCopy=PyroURI(self._pyroUri)
        return Proxy(uriCopy)
    def _pyroRelease(self):
        """release the connection to the pyro daemon"""
        if self._pyroConnection:
            self._pyroConnection.close()
            self._pyroConnection=None
    def _pyroBind(self):
        """Bind this proxy to the exact object from the uri. That means that the proxy's uri
        will be updated with a direct PYRO uri, if it isn't one yet."""
        self._pyroRelease()
        self._pyroCreateConnection(True)
    def _pyroInvoke(self, methodname, vargs, kwargs):
        """perform the remote method call communication"""
        if not self._pyroConnection:
            # rebind here, don't do it from inside the invoke because deadlock will occur
            self._pyroCreateConnection()
        data,compressed=self._pyroSerializer.serialize( (self._pyroConnection.objectId,methodname,vargs,kwargs), compress=Pyro.config.COMPRESSION )
        flags=0
        if compressed:
            flags |= MessageFactory.FLAGS_COMPRESSED
        data=MessageFactory.createMessage(MessageFactory.MSG_INVOKE, data, flags)
        self._pyroConnection.send(data)
        header=self._pyroConnection.recv(MessageFactory.HEADERSIZE)
        msgType,flags,dataLen=MessageFactory.parseMessageHeader(header)
        if msgType!=MessageFactory.MSG_RESULT:
            raise ProtocolError("invalid msg type %d received" % msgType)
        data=self._pyroConnection.recv(dataLen)
        data=self._pyroSerializer.deserialize(data, compressed=flags & MessageFactory.FLAGS_COMPRESSED)
        if flags & MessageFactory.FLAGS_EXCEPTION:
            raise data
        else:
            return data
    def _pyroCreateConnection(self, replaceUri=False):
        """Connects this proxy to the remote Pyro daemon. Does connection handshake."""
        import Pyro.naming # don't import globally because of cyclic dependancy 
        uri=Pyro.naming.resolve(self._pyroUri)
        if uri.host and uri.port:
            # socket connection
            log.debug("connecting to %s",uri)
            conn=None
            try:
                sock=Pyro.socketutil.createSocket(connect=(uri.host, uri.port))
                conn=Pyro.socketutil.SocketConnection(sock, uri.object)
                # handshake
                data=MessageFactory.createMessage(MessageFactory.MSG_CONNECT, None, 0)
                conn.send(data)
                data=conn.recv(MessageFactory.HEADERSIZE)
                msgType,flags,dataLen=MessageFactory.parseMessageHeader(data)
            except Exception,x:
                if conn:
                    conn.close()
                raise CommunicationError("cannot connect: %s" % x)
            else:
                if msgType==MessageFactory.MSG_CONNECTFAIL:
                    error="connection rejected"
                    if dataLen>0:
                        error+=", reason: "+conn.recv(dataLen)
                    conn.close()
                    raise CommunicationError(error)
                elif msgType==MessageFactory.MSG_CONNECTOK:
                    self._pyroConnection=conn
                    if replaceUri:
                        self._pyroUri=uri
                    log.debug("connected to %s",self._pyroUri)
                else:
                    conn.close()
                    raise ProtocolError("invalid msg type %d received" % msgType)
        else:
            raise NotImplementedError("non-socket uri connections not yet implemented")


class MessageFactory(object):
    """internal helper class to construct Pyro protocol messages"""
    headerFmt = '!4sHHHi'    # header (id, version, msgtype, flags, dataLen)
    version=40
    HEADERSIZE=struct.calcsize(headerFmt)
    MSG_CONNECT      = 1
    MSG_CONNECTOK    = 2
    MSG_CONNECTFAIL  = 3
    MSG_INVOKE       = 4
    MSG_RESULT       = 5
    FLAGS_EXCEPTION  = 0x0001
    FLAGS_COMPRESSED = 0x0002
    MSGTYPES=dict.fromkeys((MSG_CONNECT, MSG_CONNECTOK, MSG_CONNECTFAIL, MSG_INVOKE, MSG_RESULT))
    @classmethod
    def createMessage(cls, msgType, data, flags=0):
        """creates a message containing a header followed by the given data"""
        dataLen=len(data) if data else 0
        if msgType not in cls.MSGTYPES:
            raise ProtocolError("unknown message type %d" % msgType)
        msg=struct.pack(cls.headerFmt, "PYRO", cls.version, msgType, flags, dataLen)
        if data:
            msg+=data
        return msg
    @classmethod
    def parseMessageHeader(cls, headerData):
        """Parses a message header. Returns a tuple of messagetype, messageflags, datalength.""" 
        if not headerData or len(headerData)!=cls.HEADERSIZE:
            raise ProtocolError("header data size mismatch")
        tag,ver,msgType,flags,dataLen = struct.unpack(cls.headerFmt, headerData)
        if tag!="PYRO" or ver!=cls.version:
            raise ProtocolError("invalid data or unsupported protocol version")
        if msgType not in cls.MSGTYPES:
            raise ProtocolError("unknown message type %d" % msgType)
        return msgType,flags,dataLen


class DaemonObject(object):
    """The part of the daemon that is exposed as a Pyro object."""
    def __init__(self, daemon):
        self.daemon=daemon
    def resolve(self, objectName):
        return self.daemon.resolve(objectName)
    def registered(self):
        return self.daemon.registeredObjects() 
    def ping(self):
        pass
            

class Daemon(object):
    """Pyro daemon. Contains server side logic and dispatches incoming remote method calls to the appropriate objects."""
    def __init__(self, host=None, port=None):
        super(Daemon,self).__init__()
        if not host:
            host=Pyro.config.SERVERHOST
        if not port:
            port=Pyro.config.PORT
        if Pyro.config.SERVERTYPE=="thread":
            self.transportServer=Pyro.socketutil.SocketServer_Threadpool(self, host, port)
        elif Pyro.config.SERVERTYPE=="select":
            self.transportServer=Pyro.socketutil.SocketServer_Select(self, host, port)
        else:
            raise PyroError("invalid server type '%s'" % Pyro.config.SERVERTYPE)
        self.locationStr=self.transportServer.locationStr 
        self.serializer=Pyro.util.Serializer()
        self._pyroObjectId=Pyro.constants.INTERNAL_DAEMON_GUID
        pyroObject=DaemonObject(self)
        self.objectsById={self._pyroObjectId: (Pyro.constants.DAEMON_LOCALNAME, pyroObject)}
        self.objectsByName={Pyro.constants.DAEMON_LOCALNAME: self._pyroObjectId}
        self.mustshutdown=False
        self.loopstopped=threading.Event()
        self.loopstopped.set()
    def __del__(self):
        self.close()
    def requestLoop(self):
        """Goes in a loop to service incoming requests, until someone breaks this or calls shutdown from another thread."""  
        self.mustshutdown=False
        log.info("daemon %s entering requestloop", self.locationStr)
        try:
            self.loopstopped.clear()
            self.transportServer.requestLoop(loopCondition=lambda: not self.mustshutdown)
        finally:
            self.loopstopped.set()
        log.debug("daemon exits requestloop")
    def shutdown(self):
        """Cleanly terminate a deamon that is running in the requestloop."""
        log.debug("daemon shutting down")
        self.mustshutdown=True
        self.pingConnection()
        self.close()
        log.info("daemon %s shut down", self.locationStr)
    def pingConnection(self):
        """bit of a hack to trigger a blocking server to get out of the loop, useful at clean shutdowns"""
        self.transportServer.pingConnection()
    def handshake(self, conn):
        """Perform connection handshake with new clients"""
        header=conn.recv(MessageFactory.HEADERSIZE)
        msgType,flags,dataLen=MessageFactory.parseMessageHeader(header)
        if msgType!=MessageFactory.MSG_CONNECT:
            raise ProtocolError("expected MSG_CONNECT message, got "+str(msgType))
        if dataLen>0:
            data=conn.recv(dataLen) # read away any trailing data @UnusedVariable
        msg=MessageFactory.createMessage(MessageFactory.MSG_CONNECTOK,None,0)
        conn.send(msg)
        return True
    def handleRequest(self, conn):
        """Handle incoming Pyro request. Catches any exception that may occur and
        wraps it in a reply to the calling side, as to not make this server side loop
        terminate due to exceptions caused by remote invocations."""
        try:
            header=conn.recv(MessageFactory.HEADERSIZE)
            msgType,flags,dataLen=MessageFactory.parseMessageHeader(header)
            if msgType!=MessageFactory.MSG_INVOKE:
                raise ProtocolError("invalid msg type %d received" % msgType)
            data=conn.recv(dataLen)
            objId, method, vargs, kwargs=self.serializer.deserialize(data,compressed=flags & MessageFactory.FLAGS_COMPRESSED)
            obj=self.objectsById.get(objId)
            if obj is not None:
                if kwargs and type(kwargs.iterkeys().next()) is unicode and sys.platform!="cli":
                    # IronPython sends all strings as unicode, but apply() doesn't grok unicode keywords.
                    # So we need to rebuild the keywords dict with str keys... 
                    kwargs = dict((str(k),v) for k,v in kwargs.iteritems())
                data=getattr(obj[1], method) (*vargs,**kwargs)   # this is the actual method call
            else:
                raise DaemonError("unknown object")
            data,compressed=self.serializer.serialize(data,compress=Pyro.config.COMPRESSION)
            flags=0
            if compressed:
                flags |= MessageFactory.FLAGS_COMPRESSED
            msg=MessageFactory.createMessage(MessageFactory.MSG_RESULT, data, flags)
            del data
            conn.send(msg)
        except CommunicationError,x:
            # communication errors are not caught
            raise
        except Exception,x:
            # all other errors are caught
            log.debug("Exception occurred while handling request: %s",x)
            tblines=Pyro.util.formatTraceback()
            self.sendExceptionResponse(conn, x, tblines)
            
    def sendExceptionResponse(self, connection, exc_value, tbinfo):
        """send an exception back including the local traceback info"""
        setattr(exc_value, Pyro.constants.TRACEBACK_ATTRIBUTE, tbinfo)
        data,_=self.serializer.serialize(exc_value)
        msg=MessageFactory.createMessage(MessageFactory.MSG_RESULT, data, MessageFactory.FLAGS_EXCEPTION)
        del data
        connection.send(msg)

    def close(self):
        """Close down the server and release resources"""
        if hasattr(self,"transportServer"):
            self.transportServer.close()
    def register(self, obj, name=None):
        """Register a Pyro object under the given (local) name. Note that this object
        is now only known inside this daemon, it is not automatically available in a name server."""
        if not hasattr(obj,"_pyroObjectId"):
            obj._pyroObjectId=str(uuid.uuid4())
        if obj._pyroObjectId in self.objectsById or name in self.objectsByName:
            raise DaemonError("object already registered")
        self.objectsById[obj._pyroObjectId]=(name,obj)
        if name:
            self.objectsByName[name]=obj._pyroObjectId
    def unregister(self, objectIdOrName):
        """Remove an object from the known objects inside this daemon.
        You can unregister by objectId or by (local) object name."""
        if objectIdOrName in (Pyro.constants.INTERNAL_DAEMON_GUID, Pyro.constants.DAEMON_LOCALNAME):
            return
        obj=self.objectsById.get(objectIdOrName)
        if obj:
            del self.objectsById[objectIdOrName]
            if obj[0]:
                del self.objectsByName[obj[0]]
        else:
            obj=self.objectsByName.get(objectIdOrName)
            if obj:
                del self.objectsByName[objectIdOrName]
                del self.objectsById[obj]
    def uriFor(self, obj=None, name=None, pyroloc=False):
        """Get a PyroURI for the given object (or object name) from this daemon.
        Only a daemon can hand out proper uris because the access location is contained in them."""
        if pyroloc:
            if obj is not None:
                name=self.objectsById[obj._pyroObjectId][0]
            elif type(name) is not str:
                raise TypeError("name must be str")
            if name is None:
                raise DaemonError("object is not registered with a name")
            return PyroURI("PYROLOC:"+name+"@"+self.locationStr)
        else:
            if obj is not None:
                name=getattr(obj,"_pyroObjectId",None)
                if name is None:
                    raise DaemonError("object isn't registered")
            elif type(name) is not str:
                raise TypeError("name must be str")
            return PyroURI("PYRO:"+name+"@"+self.locationStr)
    def resolve(self, objectName):
        """Get a PyroURI for the given object name known by this daemon."""
        objId=self.objectsByName.get(objectName)
        if objId:
            return self.uriFor(name=objId)
        else:
            log.debug("unknown object: %s",objectName)
            raise NamingError("unknown object")
    def registeredObjects(self):
        """Cough up the dict of known object names and their instances."""
        return self.objectsByName
    def __str__(self):
        return "<Pyro Daemon on "+self.locationStr+">"

