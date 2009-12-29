"""
Pyro name server and helper functions.
"""

import re,logging
import Pyro.core
import Pyro.constants
from Pyro.errors import PyroError, NamingError

log=logging.getLogger("Pyro.naming")

class NameServer(object):
    """Pyro name server. Provides a simple flat name space to map logical object names to Pyro URIs."""
    def __init__(self):
        self.namespace={}
        log.info("nameserver initialized")
    def lookup(self,arg):
        try:
            return self.namespace[arg]
        except KeyError:
            raise NamingError("unknown name")
    def register(self,name,uri):
        if name in self.namespace:
            raise NamingError("name already registered")
        self.namespace[name]=uri
    def remove(self,name):
        if name in self.namespace:
            del self.namespace[name]
    def list(self, prefix=None, regex=None):
        if prefix:
            result={}
            for name,value in self.namespace.items():
                if name.startswith(prefix):
                    result[name]=value
            return result
        elif regex:
            result={}
            regex=re.compile(regex)
            for name,value in self.namespace.items():
                if regex.match(name):
                    result[name]=value
            return result
        else:
            # just return everything
            return self.namespace
    def ping(self):
        pass


class NameServerDaemon(Pyro.core.Daemon):
    """Daemon that contains the Name Server."""
    def __init__(self, host=None, port=None):
        if not host:
            host=Pyro.config.DEFAULT_SERVERHOST
        if not port:
            port=Pyro.config.DEFAULT_NS_PORT
        super(NameServerDaemon,self).__init__(host,port)
        self.ns=NameServer()
        self.register(self.ns, Pyro.constants.NAMESERVER_NAME)
        self.ns.register(Pyro.constants.NAMESERVER_NAME, self.uriFor(self.ns))
        log.info("nameserver daemon running on %s",self.locationStr)


def startNS(host=None, port=None):
    daemon=NameServerDaemon(host, port)
    try:
        print "NS running on",daemon.locationStr
        print "URI =",daemon.uriFor(daemon.ns)
        daemon.requestLoop()
    finally:
        daemon.close()
    print "NS shut down."


def locateNS(location=None):
    """Get a proxy for a name server somewhere in the network."""
    uristring="PYRONAME:"+Pyro.constants.NAMESERVER_NAME
    if location:
        uristring+="@"+location
    uri=Pyro.core.PyroURI(uristring)
    if uri.sockname or uri.pipename:
        uri.protocol="PYROLOC"
        log.debug("locating the NS: %s",uri)
        resolved=resolve(uri)
        log.debug("located NS: %s",resolved)
        return Pyro.core.Proxy(resolved)
    else:
        if not uri.host:
            raise NotImplementedError("name server network discovery not yet implemented")
        uri.protocol="PYROLOC"
        log.debug("locating the NS: %s",uri)
        resolved=resolve(uri)
        log.debug("located NS: %s",resolved)
        return Pyro.core.Proxy(resolved)


def resolve(uri):
    """Resolve a 'magic' uri (PYRONAME, PYROLOC) into the direct PYRO uri."""
    if isinstance(uri, basestring):
        uri=Pyro.core.PyroURI(uri)
    elif not isinstance(uri, Pyro.core.PyroURI):
        raise TypeError("can only resolve Pyro URIs")
    if uri.protocol=="PYRO":
        return uri
    log.debug("resolving %s",uri)
    if uri.protocol=="PYROLOC":
        daemonuri=Pyro.core.PyroURI(uri)
        daemonuri.protocol="PYRO"
        daemonuri.object=Pyro.constants.INTERNAL_DAEMON_GUID
        daemon=Pyro.core.Proxy(daemonuri)
        return daemon.resolve(uri.object)
    elif uri.protocol=="PYRONAME":
        ns=locateNS(uri.location)
        return ns.lookup(uri.object)
    else:
        raise PyroError("invalid uri protocol")
            

if __name__=="__main__":
    startNS()
