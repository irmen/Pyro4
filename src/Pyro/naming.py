
import Pyro.core
import Pyro.constants

class NameServer(object):
    @classmethod
    def locate(cls, location=None):
        uristring="PYRONAME:"+Pyro.constants.NAMESERVER_NAME
        if location:
            uristring+="@"+location
        uri=Pyro.core.PyroURI(uristring)
        if uri.sockname or uri.pipename:
            uri.protocol="PYROLOC"
            return resolve(uri)
        else:
            if not uri.host:
                raise NotImplementedError("name server network discovery not yet implemented")
            uri.protocol="PYROLOC"
            return resolve(uri)
    
def resolve(uri):
    if isinstance(uri, basestring):
        uri=Pyro.core.PyroURI(uri)
    elif not isinstance(uri, Pyro.core.PyroURI):
        raise TypeError("can only resolve Pyro URIs")
    if uri.protocol=="PYROLOC":
        daemonuri=Pyro.core.PyroURI(uri)
        daemonuri.protocol="PYRO"
        daemonuri.object=Pyro.constants.INTERNAL_DAEMON_GUID
        daemon=Pyro.core.Proxy(daemonuri)
        return daemon.resolve(uri.object)
    if uri.protocol=="PYRONAME":
        nsuri=NameServer.locate(uri.location)
        ns=Pyro.core.Proxy(nsuri)
        return ns.resolve(uri)
    else:
        return uri
            
         