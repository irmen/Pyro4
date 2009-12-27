import re
import logging
import struct
import uuid
from Pyro.errors import *
import Pyro.config
import Pyro.socketutil
import Pyro.util
import Pyro.naming

__all__=["PyroURI"]

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
            self._parseLocation(location, Pyro.config.DEFAULT_NS_PORT)
            return
        if self.protocol in ("PYRO","PYROLOC"):
            if not location:
                raise NamingError("invalid uri")
            self._parseLocation(location, Pyro.config.DEFAULT_PORT)
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
        return "<PyroURI "+str(self)+">"
    def __getstate__(self):
        return (self.protocol, self.object, self.pipename, self.sockname, self.host, self.port)
    def __setstate__(self,state):
        self.protocol, self.object, self.pipename, self.sockname, self.host, self.port = state
    def __eq__(self,other):
        return (self.protocol, self.object, self.pipename, self.sockname, self.host, self.port) \
                == (other.protocol, other.object, other.pipename, other.sockname, other.host, other.port)


class ObjBase(object):
    def __init__(self):
        self._pyroObjectId=str(uuid.uuid4())
        self._pyroUri=None


class _RemoteMethod(object):
    # method call abstraction, adapted from Python's xmlrpclib
    # it would be rather easy to add nested method calls, but
    # that is not compatible with the way that Pyro's method
    # calls are defined to work ( no nested calls ) 
    def __init__(self, send, name):
        self.__send = send
        self.__name = name
    def __call__(self, *args, **kwargs):
        return self.__send(self.__name, args, kwargs)




class Proxy(object):
    """Pyro proxy for a remote object."""
    def __init__(self, uri):
        if isinstance(uri, basestring):
            uri=Pyro.core.PyroURI(uri)
        elif not isinstance(uri, Pyro.core.PyroURI):
            raise TypeError("expected Pyro URI")
        self._pyroUri=uri
        self._pyroConnection=None
        self._pyroSerializer=Pyro.util.Serializer()
    def __getattr__(self, name):
        if name in ("__getnewargs__","__getinitargs__"):        # allows it to be safely pickled
            raise AttributeError()
        return _RemoteMethod(self._pyroInvoke, name)
    def _pyroRelease(self):
        if self._pyroConnection:
            self._pyroConnection.close()
            self._pyroConnection=None
    def _pyroInvoke(self, methodname, vargs, kwargs):
        log.debug("invoke method %s", methodname)
        if not self._pyroConnection:
            # rebind here, don't do it from inside the invoke because deadlock will occur
            self._pyroCreateConnection()
            log.debug("connected to %s",self._pyroUri)
        data=self._pyroSerializer.serialize( (self._pyroConnection.objectId,methodname,vargs,kwargs) )
        data=MessageFactory.createMessage(MessageFactory.MSG_INVOKE, data, 0)
        self._pyroConnection.send(data)
        header=self._pyroConnection.recv(MessageFactory.HEADERSIZE)
        msgType,flags,dataLen=MessageFactory.parseMessageHeader(header)
        if msgType!=MessageFactory.MSG_RESULT:
            raise ProtocolError("invalid msg type %d received" % msgType)
        data=self._pyroConnection.recv(dataLen)
        return self._pyroSerializer.deserialize(data)
    def _pyroCreateConnection(self):
        uri=Pyro.naming.resolve(self._pyroUri)
        if uri.host and uri.port:
            # socket connection
            log.info("connecting to %s",uri)
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
                    log.info("connected")
                    self._pyroConnection=conn
                else:
                    conn.close()
                    raise ProtocolError("invalid msg type %d received" % msgType)
        else:
            raise NotImplemented("non-socket uri connections not yet implemented")


class MessageFactory(object):
    headerFmt = '!4sHHHi'    # header (id, version, msgtype, flags, dataLen)
    version=40
    HEADERSIZE=struct.calcsize(headerFmt)
    MSG_CONNECT     = 1
    MSG_CONNECTOK   = 2
    MSG_CONNECTFAIL = 3
    MSG_INVOKE      = 4
    MSG_RESULT      = 5
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



    

class Daemon(ObjBase):
    """Pyro daemon. Contains server side logic and dispatches incoming remote method
    calls to the appropriate objects."""
    def __init__(self, transportServer=None, socketAddress=None):
        super(Daemon,self).__init__()
        if transportServer:
            self.transportServer=transportServer
        else:
            if socketAddress:
                self.transportServer=Pyro.socketutil.SocketServer(self, socketAddress[0], socketAddress[1])
            else:
                self.transportServer=Pyro.socketutil.SocketServer(self, "localhost", Pyro.config.DEFAULT_PORT)
            self.location=self.transportServer.sock.getsockname() 
        self.serializer=Pyro.util.Serializer()
        self._pyroObjectId=Pyro.constants.INTERNAL_DAEMON_GUID
        self.objectsById={self._pyroObjectId: (Pyro.constants.DAEMON_NAME, self)}
        self.objectsByName={Pyro.constants.DAEMON_NAME: self._pyroObjectId}
    def requestLoop(self):
        self.transportServer.requestLoop()
    def handshake(self, conn):
        header=conn.recv(MessageFactory.HEADERSIZE)
        msgType,flags,dataLen=MessageFactory.parseMessageHeader(header)
        if msgType!=MessageFactory.MSG_CONNECT:
            raise ProtocolError("expected MSG_CONNECT message, got "+str(msgType))
        if dataLen>0:
            data=conn.recv(dataLen)
        msg=MessageFactory.createMessage(MessageFactory.MSG_CONNECTOK,None,0)
        conn.send(msg)
        return True
    def handleRequest(self, conn):
        header=conn.recv(MessageFactory.HEADERSIZE)
        msgType,flags,dataLen=MessageFactory.parseMessageHeader(header)
        if msgType!=MessageFactory.MSG_INVOKE:
            raise ProtocolError("invalid msg type %d received" % msgType)
        data=self.serializer.deserialize(conn.recv(dataLen))
        data=self.invoke(data)
        data=self.serializer.serialize(data)
        msg=MessageFactory.createMessage(MessageFactory.MSG_RESULT, data, 0)
        del data
        conn.send(msg)
    def invoke(self, data):
        objId, method, vargs, kwargs=data
        log.info("remote invocation for %s method %s" % (objId,method))
        obj=self.objectsById.get(objId)
        if obj is not None:
            return getattr(obj[1], method) (*vargs,**kwargs)
        else:
            raise PyroError("unknown object")
    def close(self):
        self.transportServer.close()
    def register(self, object, name=None):
        if object._pyroObjectId in self.objectsById or name in self.objectsByName:
            raise DaemonError("object already registered")
        self.objectsById[object._pyroObjectId]=(name,object)
        if name:
            self.objectsByName[name]=object._pyroObjectId
    def unregister(self, objectIdOrName):
        if objectIdOrName in (Pyro.constants.INTERNAL_DAEMON_GUID, Pyro.constants.DAEMON_NAME):
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
    def uriFor(self, obj):
        if isinstance(obj, ObjBase):
            obj=obj._pyroObjectId
        return PyroURI("PYRO:"+obj+"@"+self.transportServer.locationStr)
    def resolve(self, objectName):
        log.debug("daemon.resolve "+objectName)
        obj=self.objectsByName.get(objectName)
        if obj:
            return self.uriFor(obj)
        else:
            raise NamingError("unknown object")
    def registeredObjects(self):
        return self.objectsByName

