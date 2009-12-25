import logging
import Pyro.core
import Pyro.constants

log=logging.getLogger("Pyro.naming")

class NameServer(object):
    """Pyro name server.
    Provides a hierarchical name space to map logical object names to Pyro URIs.
    """
    
    @classmethod
    def locate(cls, location=None):
        """classmethod to be able to get a proxy for a name server easily."""
        uristring="PYRONAME:"+Pyro.constants.NAMESERVER_NAME
        if location:
            uristring+="@"+location
        uri=Pyro.core.PyroURI(uristring)
        log.debug("locating the NS: %s",uri)
        if uri.sockname or uri.pipename:
            uri.protocol="PYROLOC"
            resolved=resolve(uri)
            log.debug("located NS: %s",resolved)
            return Pyro.core.Proxy(resolved)
        else:
            if not uri.host:
                raise NotImplementedError("name server network discovery not yet implemented")
            uri.protocol="PYROLOC"
            resolved=resolve(uri)
            log.debug("located NS: %s",resolved)
            return Pyro.core.Proxy(resolved)

def resolve(uri):
    """resolve a 'magic' uri (PYRONAME, PYROLOC) to the direct PYRO uri."""
    if isinstance(uri, basestring):
        uri=Pyro.core.PyroURI(uri)
    elif not isinstance(uri, Pyro.core.PyroURI):
        raise TypeError("can only resolve Pyro URIs")
    log.debug("resolving %s",uri)
    if uri.protocol=="PYROLOC":
        daemonuri=Pyro.core.PyroURI(uri)
        daemonuri.protocol="PYRO"
        daemonuri.object=Pyro.constants.INTERNAL_DAEMON_GUID
        daemon=Pyro.core.Proxy(daemonuri)
        return daemon.resolve(uri.object)
    if uri.protocol=="PYRONAME":
        ns=NameServer.locate(uri.location)
        return ns.resolve(uri)
    else:
        return uri  # uri is already a direct PYRO reference
            
