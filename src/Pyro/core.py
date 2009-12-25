import re
import logging
from Pyro.errors import NamingError
import Pyro.config

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



class Proxy(object):
    """Pyro proxy for a remote object."""
    def __init__(self, uri):
        if isinstance(uri, basestring):
            uri=Pyro.core.PyroURI(uri)
        elif not isinstance(uri, Pyro.core.PyroURI):
            raise TypeError("expected Pyro URI")
        self._pyroUri=uri
        self._pyroObjectId=uri.object
    def resolve(self, localobjectname):
        # @todo: this shouldn't be a static method, but called remotely
        # this stubs the resolve method on a pyro daemon / resolve method on name server
        log.info("temp stub Proxy.resolve "+str(localobjectname))
        resolved=Pyro.core.PyroURI(self._pyroUri)
        resolved.protocol="PYRO"
        resolved.object="999999999999"
        return resolved

