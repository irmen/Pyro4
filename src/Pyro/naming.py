"""
Pyro name server and helper functions.
"""

import re,logging
import threading
import socket
import Pyro.core
import Pyro.constants
import Pyro.socketutil
from Pyro.errors import PyroError, NamingError, TimeoutError

log=logging.getLogger("Pyro.naming")

class NameServer(object):
    """Pyro name server. Provides a simple flat name space to map logical object names to Pyro URIs."""
    def __init__(self):
        self.namespace={}
        log.info("nameserver initialized")
    def lookup(self,arg):
        try:
            return Pyro.core.PyroURI(self.namespace[arg])
        except KeyError:
            raise NamingError("unknown name")
    def register(self,name,uri):
        if isinstance(uri, Pyro.core.PyroURI):
            uri=str(uri)
        elif type(uri) is not str:
            raise TypeError("only PyroURIs or strings can be registered")
        if type(name) is not str:
            raise TypeError("name must be a str")
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
            try:
                regex=re.compile(regex+"$")  # add end of string marker
            except re.error,x:
                raise NamingError("invalid regex: "+str(x))
            else:
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
            host=Pyro.config.SERVERHOST
        if not port:
            port=Pyro.config.NS_PORT
        super(NameServerDaemon,self).__init__(host,port)
        self.ns=NameServer()
        self.register(self.ns, Pyro.constants.NAMESERVER_NAME)
        self.ns.register(Pyro.constants.NAMESERVER_NAME, self.uriFor(self.ns))
        log.info("nameserver daemon running on %s",self.locationStr)


class BroadcastServer(threading.Thread):
    def __init__(self, nsUri, bchost=None, bcport=None):
        super(BroadcastServer,self).__init__()
        self.nsUri=str(nsUri)
        self.running=True
        bcport=bcport or Pyro.config.NS_BCPORT
        bchost=bchost or Pyro.config.NS_BCHOST
        self.sock=Pyro.socketutil.createBroadcastSocket((bchost,bcport))
        if bchost:
            self.locationStr="%s:%d" % (bchost, bcport)
        else:
            self.locationStr="%s:%d" % self.sock.getsockname()
    def run(self):
        log.info("broadcast server listening")
        self.sock.settimeout(3)
        while self.running:
            try:
                data,addr=self.sock.recvfrom(100)
                if data=="GET_NSURI":
                    self.sock.sendto(self.nsUri, addr)
            except socket.timeout:
                continue
            except socket.error,x:
                log.info("broadcast server got an error: %s",x)
                continue
        log.info("broadcast server exits")
    def close(self):
        self.running=False
        self.sock.close()


def startNS(host=None, port=None, enableBroadcast=True, bchost=None, bcport=None):
    daemon=NameServerDaemon(host, port)
    if daemon.locationStr.startswith("127.0.0.1:") or daemon.locationStr.startswith("localhost:"):
        print "Not starting broadcast server for localhost."
        enableBroadcast=False
    nsUri=daemon.uriFor(daemon.ns)
    bcserver=None
    if enableBroadcast:
        bcserver=BroadcastServer(nsUri,bchost,bcport)
        bcserver.daemon=True
        bcserver.start()
        print "Broadcast server running on", bcserver.locationStr  
    print "NS running on",daemon.locationStr
    print "URI =",nsUri
    try:
        daemon.requestLoop()
    finally:
        daemon.close()
        if bcserver is not None:
            bcserver.close()
    print "NS shut down."


def locateNS(host=None, port=None):
    """Get a proxy for a name server somewhere in the network."""
    if host is None:
        # broadcast lookup
        if not port:
            port=Pyro.config.NS_BCPORT
        log.debug("broadcast locate")
        sock=Pyro.socketutil.createBroadcastSocket(timeout=0.7)
        for i in range(3):
            try:
                sock.sendto("GET_NSURI",("<broadcast>",port))
                data,addr=sock.recvfrom(100)
                log.debug("located NS: %s",data)
                return Pyro.core.Proxy(data)
            except socket.timeout:
                continue
        raise TimeoutError("timeout locating name server")
    # pyroloc lookup
    if not port:
        port=Pyro.config.NS_PORT
    uristring="PYROLOC:%s@%s:%d" % (Pyro.constants.NAMESERVER_NAME,host,port)
    uri=Pyro.core.PyroURI(uristring)
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
        ns=locateNS(uri.host, uri.port)
        return ns.lookup(uri.object)
    else:
        raise PyroError("invalid uri protocol")
            

def main(args):
    from optparse import OptionParser
    parser=OptionParser()
    parser.add_option("-n","--host", dest="host", help="hostname to bind server on")
    parser.add_option("-p","--port", dest="port", type="int", help="port to bind server on")
    parser.add_option("","--bchost", dest="bchost", help="hostname to bind broadcast server on")
    parser.add_option("","--bcport", dest="bcport", type="int", help="port to bind broadcast server on")
    parser.add_option("-x","--nobc", dest="enablebc", action="store_false", default=True, help="don't start a broadcast server")
    options,args = parser.parse_args(args)    
    startNS(options.host,options.port,enableBroadcast=options.enablebc,bchost=options.bchost,bcport=options.bcport)

if __name__=="__main__":
    import sys
    main(sys.argv[1:])
