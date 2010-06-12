"""
Name Server and helper functions.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong.
irmen@razorvine.net - http://www.razorvine.net/python/Pyro
"""

from __future__ import with_statement
import re, logging, socket
from Pyro.threadutil import RLock, Thread
import Pyro.core        # not Pyro.core, to avoid circular import
import Pyro.constants
import Pyro.socketutil
from Pyro.errors import PyroError, NamingError

__all__=["locateNS","resolve"]

log=logging.getLogger("Pyro.naming")

class NameServer(object):
    """Pyro name server. Provides a simple flat name space to map logical object names to Pyro URIs."""
    def __init__(self):
        self.namespace={}
        self.lock=RLock()
    def lookup(self,arg):
        try:
            return Pyro.core.URI(self.namespace[arg])
        except KeyError:
            raise NamingError("unknown name: "+arg)
    def register(self,name,uri):
        if isinstance(uri, Pyro.core.URI):
            uri=uri.asString()
        elif not isinstance(uri, basestring):
            raise TypeError("only URIs or strings can be registered")
        else:
            Pyro.core.URI(uri)  # check if uri is valid
        if not isinstance(name, basestring):
            raise TypeError("name must be a str")
        if name in self.namespace:
            raise NamingError("name already registered: "+name)
        with self.lock:
            self.namespace[name]=uri
    def remove(self, name=None, prefix=None, regex=None):
        if name and name in self.namespace and name!=Pyro.constants.NAMESERVER_NAME:
            with self.lock:
                del self.namespace[name]
            return 1
        if prefix:
            with self.lock:
                items=list(self.list(prefix=prefix).keys())
                if Pyro.constants.NAMESERVER_NAME in items:
                    items.remove(Pyro.constants.NAMESERVER_NAME)
                for item in items:
                    del self.namespace[item]
                return len(items)
        if regex:
            with self.lock:
                items=list(self.list(regex=regex).keys())
                if Pyro.constants.NAMESERVER_NAME in items:
                    items.remove(Pyro.constants.NAMESERVER_NAME)
                for item in items:
                    del self.namespace[item]
                return len(items)
        return 0

    def list(self, prefix=None, regex=None):
        with self.lock:
            if prefix:
                result={}
                for name in self.namespace:
                    if name.startswith(prefix):
                        result[name]=self.namespace[name]
                return result
            elif regex:
                result={}
                try:
                    regex=re.compile(regex+"$")  # add end of string marker
                except re.error,x:
                    raise NamingError("invalid regex: "+str(x))
                else:
                    for name in self.namespace:
                        if regex.match(name):
                            result[name]=self.namespace[name]
                    return result
            else:
                # just return (a copy of) everything
                return self.namespace.copy()
    def ping(self):
        pass


class NameServerDaemon(Pyro.core.Daemon):
    """Daemon that contains the Name Server."""
    def __init__(self, host=None, port=None):
        if Pyro.config.DOTTEDNAMES:
            raise PyroError("Name server won't start with DOTTEDNAMES enabled because of security reasons")
        if host is None:
            host=Pyro.config.HOST
        if port is None:
            port=Pyro.config.NS_PORT
        super(NameServerDaemon,self).__init__(host,port)
        self.nameserver=NameServer()
        self.register(self.nameserver, Pyro.constants.NAMESERVER_NAME)
        self.nameserver.register(Pyro.constants.NAMESERVER_NAME, self.uriFor(self.nameserver))
        log.info("nameserver daemon created")
    def close(self):
        super(NameServerDaemon,self).close()
        self.nameserver=None
    def __enter__(self):
        if not self.nameserver:
            raise PyroError("cannot reuse this object")
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.nameserver=None
        return super(NameServerDaemon,self).__exit__(exc_type, exc_value, traceback)
        
class BroadcastServer(object):
    def __init__(self, nsUri, bchost=None, bcport=None):
        self.nsUri=str(nsUri)
        if bcport is None:
            bcport=Pyro.config.NS_BCPORT
        if bchost is None:
            bchost=Pyro.config.NS_BCHOST
        self.sock=Pyro.socketutil.createBroadcastSocket((bchost,bcport), timeout=2.0)
        self._sockaddr=self.sock.getsockname()
        bchost=bchost or self._sockaddr[0]
        bcport=bcport or self._sockaddr[1]
        self.locationStr="%s:%d" % (bchost, bcport)
        log.info("ns broadcast server created on %s",self.locationStr)
        self.running=True
    def close(self):
        log.debug("ns broadcast server closing")
        self.running=False
        self.sock.close()
    def getPort(self):
        return self.sock.getsockname()[1]
    def fileno(self):
        return self.sock.fileno()
    def runInThread(self):
        """Run the broadcast server loop in its own thread. This is mainly for Jython,
        which has problems with multiplexing it using select() with the Name server itself."""
        thread=Thread(target=self.__requestLoop)
        thread.setDaemon(True)
        thread.start()
        log.debug("broadcast server loop running in own thread")
    def __requestLoop(self):
        while self.running:
            self.processRequest()
        log.debug("broadcast server loop terminating")
    def processRequest(self):
        try:
            data,addr=self.sock.recvfrom(100)
            if data=="GET_NSURI":
                log.debug("responding to broadcast request from %s",addr)
                self.sock.sendto(self.nsUri, addr)
        except socket.error:
            pass
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

def startNSloop(host=None, port=None, enableBroadcast=True, bchost=None, bcport=None):
    """utility function that starts a new Name server and enters its requestloop."""
    daemon=NameServerDaemon(host, port)
    hostip=daemon.sock.getsockname()[0]
    nsUri=daemon.uriFor(daemon.nameserver)
    if hostip.startswith("127."):
        print "Not starting broadcast server for localhost."
        log.info("Not starting NS broadcast server because NS is bound to localhost")
        enableBroadcast=False
    bcserver=None
    if enableBroadcast:
        bcserver=BroadcastServer(nsUri,bchost,bcport)
        print "Broadcast server running on", bcserver.locationStr
        bcserver.runInThread()  
    print "NS running on %s (%s)" % (daemon.locationStr,hostip)
    print "URI =",nsUri
    try:
        daemon.requestLoop()
    finally:
        daemon.close()
        if bcserver is not None:
            bcserver.close()
    print "NS shut down."

def startNS(host=None, port=None, enableBroadcast=True, bchost=None, bcport=None):
    """utility fuction to quickly get a Name server daemon to be used in your own event loops.
    Returns (nameserverUri, nameserverDaemon, broadcastServer)."""
    daemon=NameServerDaemon(host, port)
    nsUri=daemon.uriFor(daemon.nameserver)
    hostip=daemon.sock.getsockname()[0]
    if hostip.startswith("127."):
        # not starting broadcast server for localhost.
        enableBroadcast=False
    bcserver=None
    if enableBroadcast:
        bcserver=BroadcastServer(nsUri,bchost,bcport)
    return nsUri, daemon, bcserver

def locateNS(host=None, port=None):
    """Get a proxy for a name server somewhere in the network."""
    if host is None:
        # first try localhost if we have a good chance of finding it there
        if Pyro.config.NS_HOST=="localhost" or Pyro.config.NS_HOST.startswith("127."):
            uristring="PYRO:%s@%s:%d" % (Pyro.constants.NAMESERVER_NAME, Pyro.config.NS_HOST, port or Pyro.config.NS_PORT)
            log.debug("locating the NS: %s",uristring)
            proxy=Pyro.core.Proxy(uristring)
            try:
                proxy.ping()
                log.debug("located NS")
                return proxy
            except PyroError:
                pass
        # broadcast lookup
        if not port:
            port=Pyro.config.NS_BCPORT
        log.debug("broadcast locate")
        sock=Pyro.socketutil.createBroadcastSocket(timeout=0.7)
        for _ in range(3):
            try:
                sock.sendto("GET_NSURI",("<broadcast>",port))
                data,_=sock.recvfrom(100)
                sock.close()
                log.debug("located NS: %s",data)
                return Pyro.core.Proxy(data)
            except socket.timeout:
                continue
        sock.close()
        log.debug("broadcast locate failed, try direct connection on NS_HOST")
        # broadcast failed, try PYRO directly on specific host
        host=Pyro.config.NS_HOST
        port=Pyro.config.NS_PORT
    # pyro direct lookup
    if not port:
        port=Pyro.config.NS_PORT
    if Pyro.core.URI.isPipeOrUnixsockLocation(host):
        uristring="PYRO:%s@%s" % (Pyro.constants.NAMESERVER_NAME,host)
    else:
        uristring="PYRO:%s@%s:%d" % (Pyro.constants.NAMESERVER_NAME,host,port)
    uri=Pyro.core.URI(uristring)
    log.debug("locating the NS: %s",uri)
    proxy=Pyro.core.Proxy(uri)
    try:
        proxy.ping()
        log.debug("located NS")
        return proxy
    except PyroError:
        raise Pyro.errors.NamingError("Failed to locate the nameserver")
        
    

def resolve(uri):
    """Resolve a 'magic' uri (PYRONAME) into the direct PYRO uri."""
    if isinstance(uri, basestring):
        uri=Pyro.core.URI(uri)
    elif not isinstance(uri, Pyro.core.URI):
        raise TypeError("can only resolve Pyro URIs")
    if uri.protocol=="PYRO":
        return uri
    log.debug("resolving %s",uri)
    if uri.protocol=="PYRONAME":
        nameserver=locateNS(uri.host, uri.port)
        uri=nameserver.lookup(uri.object)
        nameserver._pyroRelease()
        return uri
    else:
        raise PyroError("invalid uri protocol")

def main(args):
    from optparse import OptionParser
    parser=OptionParser()
    parser.add_option("-n","--host", dest="host", help="hostname to bind server on")
    parser.add_option("-p","--port", dest="port", type="int", help="port to bind server on (0=random)")
    parser.add_option("","--bchost", dest="bchost", help="hostname to bind broadcast server on")
    parser.add_option("","--bcport", dest="bcport", type="int", 
                      help="port to bind broadcast server on (0=random)")
    parser.add_option("-x","--nobc", dest="enablebc", action="store_false", default=True,
                      help="don't start a broadcast server")
    options,args = parser.parse_args(args)
    startNSloop(options.host,options.port,enableBroadcast=options.enablebc,
            bchost=options.bchost,bcport=options.bcport)

if __name__=="__main__":
    import sys
    main(sys.argv[1:])
