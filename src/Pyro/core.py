import re
from Pyro.errors import NamingError

DEFAULT_PORT=7766

class PyroURI(object):
    """Pyro object URI (universal resource identifier)
    PYRO uri format: PYRO:objectid@location
        where location is one of:
          hostname       (tcp/ip socket on default port)
          hostname:port  (tcp/ip socket on given port)
          ./p:pipename   (named pipe on localhost)
          ./u:sockname   (unix domain socket on localhost)
    
    MAGIC URI formats:
      PYRONAME:logicalobjectname
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
            if location:
                raise NamingError("invalid uri")
            return
        if self.protocol in ("PYRO","PYROLOC"):
            if not location:
                raise NamingError("invalid uri")
            if location.startswith("./p:"):
                self.pipename=location[4:]
                if not self.pipename:
                    raise NamingError("invalid uri (pipe)")
            elif location.startswith("./u:"):
                self.sockname=location[4:]
                if not self.sockname:
                    raise NamingError("invalid uri (socket)")
            else:
                self.host,_,self.port=location.partition(":")
                if not self.port:
                    self.port=DEFAULT_PORT
                else:
                    try:
                        self.port=int(self.port)
                    except ValueError:
                        raise NamingError("invalid uri (port)")
        else:
            raise NamingError("invalid uri (protocol)")
    def __str__(self):
        if self.protocol=="PYRONAME":
            return "PYRONAME:"+self.object
        if self.host:
            location="%s:%d" % (self.host, self.port)
        elif self.sockname:
            location="./u:"+self.sockname
        elif self.pipename:
            location="./p:"+self.pipename
        return self.protocol+":"+self.object+"@"+location
    def __repr__(self):
        return "<PyroURI "+str(self)+">"
    def __getstate__(self):
        return (self.protocol, self.object, self.pipename, self.sockname, self.host, self.port)
    def __setstate__(self,state):
        self.protocol, self.object, self.pipename, self.sockname, self.host, self.port = state
    def __eq__(self,other):
        return (self.protocol, self.object, self.pipename, self.sockname, self.host, self.port) \
                == (other.protocol, other.object, other.pipename, other.sockname, other.host, other.port)
