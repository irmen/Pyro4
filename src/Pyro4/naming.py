"""
Name Server and helper functions.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import warnings
import re
import logging
import socket
import sys
from Pyro4.threadutil import RLock, Thread
from Pyro4.errors import NamingError, PyroError, ProtocolError
from Pyro4 import core, socketutil
import Pyro4.constants

__all__ = ["locateNS", "resolve", "startNS", "startNSloop", "MemoryStorage"]

if sys.version_info >= (3, 0):
    basestring = str

log = logging.getLogger("Pyro4.naming")


class MemoryStorage(dict):
    """
    Storage implementation that is just an in-memory dict.
    Stopping the nameserver will make the server instantly forget about everything.
    """
    def __init__(self, **kwargs):
        super(MemoryStorage, self).__init__(**kwargs)

    def optimized_prefix_list(self, prefix):
        return None

    def optimized_regex_list(self, regex):
        return None

    def everything(self):
        return self.copy()

    def remove_items(self, items):
        for item in items:
            try:
                del self[item]
            except KeyError:
                pass

    def close(self):
        pass


class NameServer(object):
    """
    Pyro name server. Provides a simple flat name space to map logical object names to Pyro URIs.
    Default storage is done in an in-memory dictionary. You can provide custom storage types.
    """
    def __init__(self, storageProvider=None):
        self.storage = storageProvider
        if storageProvider is None:
            self.storage = MemoryStorage()
            log.debug("using volatile in-memory dict storage")
        self.lock = RLock()

    def count(self):
        return len(self.storage)

    def lookup(self, name):
        """Lookup the given name, returns an URI if found"""
        try:
            return core.URI(self.storage[name])
        except KeyError:
            raise NamingError("unknown name: " + name)

    def register(self, name, uri, safe=False):
        """Register a name with an URI. If safe is true, name cannot be registered twice.
        The uri can be a string or an URI object."""
        if isinstance(uri, core.URI):
            uri = uri.asString()
        elif not isinstance(uri, basestring):
            raise TypeError("only URIs or strings can be registered")
        else:
            core.URI(uri)  # check if uri is valid
        if not isinstance(name, basestring):
            raise TypeError("name must be a str")
        with self.lock:
            if safe and name in self.storage:
                raise NamingError("name already registered: " + name)
            self.storage[name] = uri

    def remove(self, name=None, prefix=None, regex=None):
        """Remove a registration. returns the number of items removed."""
        if name and name in self.storage and name != Pyro4.constants.NAMESERVER_NAME:
            with self.lock:
                del self.storage[name]
            return 1
        if prefix:
            items = list(self.list(prefix=prefix).keys())
            if Pyro4.constants.NAMESERVER_NAME in items:
                items.remove(Pyro4.constants.NAMESERVER_NAME)
            self.storage.remove_items(items)
            return len(items)
        if regex:
            items = list(self.list(regex=regex).keys())
            if Pyro4.constants.NAMESERVER_NAME in items:
                items.remove(Pyro4.constants.NAMESERVER_NAME)
            self.storage.remove_items(items)
            return len(items)
        return 0

    # noinspection PyNoneFunctionAssignment
    def list(self, prefix=None, regex=None):
        """Retrieve the registered items as a dictionary name-to-URI. The URIs
        in the resulting dict are strings, not URI objects.
        You can filter by prefix or by regex."""
        with self.lock:
            if prefix:
                result = self.storage.optimized_prefix_list(prefix)
                if result is not None:
                    return result
                result = {}
                for name in self.storage:
                    if name.startswith(prefix):
                        result[name] = self.storage[name]
                return result
            elif regex:
                result = self.storage.optimized_regex_list(regex)
                if result is not None:
                    return result
                result = {}
                try:
                    regex = re.compile(regex + "$")  # add end of string marker
                except re.error:
                    x = sys.exc_info()[1]
                    raise NamingError("invalid regex: " + str(x))
                else:
                    for name in self.storage:
                        if regex.match(name):
                            result[name] = self.storage[name]
                    return result
            else:
                # just return (a copy of) everything
                return self.storage.everything()

    def ping(self):
        """A simple test method to check if the name server is running correctly."""
        pass


class NameServerDaemon(core.Daemon):
    """Daemon that contains the Name Server."""

    def __init__(self, host=None, port=None, unixsocket=None, nathost=None, natport=None, storage=None):
        if host is None:
            host = Pyro4.config.HOST
        if port is None:
            port = Pyro4.config.NS_PORT
        if nathost is None:
            nathost = Pyro4.config.NATHOST
        if natport is None:
            natport = Pyro4.config.NATPORT or None
        storage = storage or "memory"
        if storage == "memory":
            log.debug("using volatile in-memory dict storage")
            self.nameserver = NameServer(MemoryStorage())
        elif storage.startswith("dbm:") and len(storage) > 4:
            dbmfile = storage[4:]
            log.debug("using persistent dbm storage in file %s", dbmfile)
            from Pyro4.naming_storage import DbmStorage
            self.nameserver = NameServer(DbmStorage(dbmfile))
        elif storage.startswith("sql:") and len(storage) > 4:
            sqlfile = storage[4:]
            log.debug("using persistent sql storage in file %s", sqlfile)
            from Pyro4.naming_storage import SqlStorage
            self.nameserver = NameServer(SqlStorage(sqlfile))
        else:
            raise ValueError("invalid storage type '%s'" % storage)
        existing_count = self.nameserver.count()
        if existing_count > 0:
            log.debug("number of existing entries in storage: %d", existing_count)
        super(NameServerDaemon, self).__init__(host, port, unixsocket, nathost=nathost, natport=natport)
        self.register(self.nameserver, Pyro4.constants.NAMESERVER_NAME)
        self.nameserver.register(Pyro4.constants.NAMESERVER_NAME, self.uriFor(self.nameserver))
        log.info("nameserver daemon created")

    def close(self):
        super(NameServerDaemon, self).close()
        if self.nameserver is not None:
            self.nameserver.storage.close()
            self.nameserver = None

    def __enter__(self):
        if not self.nameserver:
            raise PyroError("cannot reuse this object")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.nameserver is not None:
            self.nameserver.storage.close()
        self.nameserver = None
        return super(NameServerDaemon, self).__exit__(exc_type, exc_value, traceback)

    def handleRequest(self, conn):
        try:
            return super(NameServerDaemon, self).handleRequest(conn)
        except ProtocolError as x:
            # Notify the user that a protocol error occurred.
            # This is useful for instance when a wrong serializer is used, it helps
            # a lot to immediately see what is going wrong.
            warnings.warn("Pyro protocol error occurred: " + str(x))
            raise


class BroadcastServer(object):
    REQUEST_NSURI = "GET_NSURI" if sys.platform == "cli" else b"GET_NSURI"

    def __init__(self, nsUri, bchost=None, bcport=None):
        self.nsUri = nsUri
        if bcport is None:
            bcport = Pyro4.config.NS_BCPORT
        if bchost is None:
            bchost = Pyro4.config.NS_BCHOST
        if ":" in nsUri.host:  # ipv6
            bchost = bchost or "::"
            self.sock = Pyro4.socketutil.createBroadcastSocket((bchost, bcport, 0, 0), reuseaddr=Pyro4.config.SOCK_REUSE, timeout=2.0)
        else:
            self.sock = Pyro4.socketutil.createBroadcastSocket((bchost, bcport), reuseaddr=Pyro4.config.SOCK_REUSE, timeout=2.0)
        self._sockaddr = self.sock.getsockname()
        bchost = bchost or self._sockaddr[0]
        bcport = bcport or self._sockaddr[1]
        if ":" in bchost:  # ipv6
            self.locationStr = "[%s]:%d" % (bchost, bcport)
        else:
            self.locationStr = "%s:%d" % (bchost, bcport)
        log.info("ns broadcast server created on %s", self.locationStr)
        self.running = True

    def close(self):
        log.debug("ns broadcast server closing")
        self.running = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except (OSError, socket.error):
            pass
        self.sock.close()

    def getPort(self):
        return self.sock.getsockname()[1]

    def fileno(self):
        return self.sock.fileno()

    def runInThread(self):
        """Run the broadcast server loop in its own thread. This is mainly for Jython,
        which has problems with multiplexing it using select() with the Name server itself."""
        thread = Thread(target=self.__requestLoop)
        thread.setDaemon(True)
        thread.start()
        log.debug("broadcast server loop running in own thread")

    def __requestLoop(self):
        while self.running:
            self.processRequest()
        log.debug("broadcast server loop terminating")

    def processRequest(self):
        try:
            data, addr = self.sock.recvfrom(100)
            if data == self.REQUEST_NSURI:
                responsedata = core.URI(self.nsUri)
                if responsedata.host == "0.0.0.0":
                    # replace INADDR_ANY address by the interface IP address that connects to the requesting client
                    try:
                        interface_ip = socketutil.getInterfaceAddress(addr[0])
                        responsedata.host = interface_ip
                    except socket.error:
                        pass
                log.debug("responding to broadcast request from %s: interface %s", addr[0], responsedata.host)
                responsedata = str(responsedata).encode("iso-8859-1")
                self.sock.sendto(responsedata, 0, addr)
        except socket.error:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def startNSloop(host=None, port=None, enableBroadcast=True, bchost=None, bcport=None, unixsocket=None, nathost=None, natport=None, storage=None, hmac=None):
    """utility function that starts a new Name server and enters its requestloop."""
    daemon = NameServerDaemon(host, port, unixsocket, nathost=nathost, natport=natport, storage=storage)
    daemon._pyroHmacKey = hmac
    nsUri = daemon.uriFor(daemon.nameserver)
    internalUri = daemon.uriFor(daemon.nameserver, nat=False)
    bcserver = None
    if unixsocket:
        hostip = "Unix domain socket"
    else:
        hostip = daemon.sock.getsockname()[0]
        if hostip.startswith("127."):
            print("Not starting broadcast server for localhost.")
            log.info("Not starting NS broadcast server because NS is bound to localhost")
            enableBroadcast = False
        if enableBroadcast:
            # Make sure to pass the internal uri to the broadcast responder.
            # It is almost always useless to let it return the external uri,
            # because external systems won't be able to talk to this thing anyway.
            bcserver = BroadcastServer(internalUri, bchost, bcport)
            print("Broadcast server running on %s" % bcserver.locationStr)
            bcserver.runInThread()
    existing = daemon.nameserver.count()
    if existing > 1:   # don't count our own nameserver registration
        print("Persistent store contains %d existing registrations." % existing)
    print("NS running on %s (%s)" % (daemon.locationStr, hostip))
    if not hmac:
        print("Warning: HMAC key not set. Anyone can connect to this server!")
    if daemon.natLocationStr:
        print("internal URI = %s" % internalUri)
        print("external URI = %s" % nsUri)
    else:
        print("URI = %s" % nsUri)
    try:
        daemon.requestLoop()
    finally:
        daemon.close()
        if bcserver is not None:
            bcserver.close()
    print("NS shut down.")


def startNS(host=None, port=None, enableBroadcast=True, bchost=None, bcport=None, unixsocket=None, nathost=None, natport=None, storage=None, hmac=None):
    """utility fuction to quickly get a Name server daemon to be used in your own event loops.
    Returns (nameserverUri, nameserverDaemon, broadcastServer)."""
    daemon = NameServerDaemon(host, port, unixsocket, nathost=nathost, natport=natport, storage=storage)
    daemon._pyroHmacKey = hmac
    bcserver = None
    nsUri = daemon.uriFor(daemon.nameserver)
    if not unixsocket:
        hostip = daemon.sock.getsockname()[0]
        if hostip.startswith("127."):
            # not starting broadcast server for localhost.
            enableBroadcast = False
        if enableBroadcast:
            internalUri = daemon.uriFor(daemon.nameserver, nat=False)
            bcserver = BroadcastServer(internalUri, bchost, bcport)
    return nsUri, daemon, bcserver


def locateNS(host=None, port=None, broadcast=True, hmac_key=None):
    """Get a proxy for a name server somewhere in the network."""
    if host is None:
        # first try localhost if we have a good chance of finding it there
        if Pyro4.config.NS_HOST in ("localhost", "::1") or Pyro4.config.NS_HOST.startswith("127."):
            host = Pyro4.config.NS_HOST
            if ":" in host:  # ipv6
                host = "[%s]" % host
            uristring = "PYRO:%s@%s:%d" % (Pyro4.constants.NAMESERVER_NAME, host, port or Pyro4.config.NS_PORT)
            log.debug("locating the NS: %s", uristring)
            proxy = core.Proxy(uristring)
            proxy._pyroHmacKey = hmac_key
            try:
                proxy.ping()
                log.debug("located NS")
                return proxy
            except PyroError:
                pass
        if broadcast:
            # broadcast lookup
            if not port:
                port = Pyro4.config.NS_BCPORT
            log.debug("broadcast locate")
            sock = Pyro4.socketutil.createBroadcastSocket(reuseaddr=Pyro4.config.SOCK_REUSE, timeout=0.7)
            for _ in range(3):
                try:
                    for bcaddr in Pyro4.config.parseAddressesString(Pyro4.config.BROADCAST_ADDRS):
                        try:
                            sock.sendto(BroadcastServer.REQUEST_NSURI, 0, (bcaddr, port))
                        except socket.error:
                            x = sys.exc_info()[1]
                            err = getattr(x, "errno", x.args[0])
                            if err not in Pyro4.socketutil.ERRNO_EADDRNOTAVAIL:  # yeah, windows likes to throw these...
                                if err not in Pyro4.socketutil.ERRNO_EADDRINUSE:  # and jython likes to throw thses...
                                    raise
                    data, _ = sock.recvfrom(100)
                    sock.close()
                    if sys.version_info >= (3, 0):
                        data = data.decode("iso-8859-1")
                    log.debug("located NS: %s", data)
                    return core.Proxy(data)
                except socket.timeout:
                    continue
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except (OSError, socket.error):
                pass
            sock.close()
            log.debug("broadcast locate failed, try direct connection on NS_HOST")
        else:
            log.debug("skipping broadcast lookup")
        # broadcast failed or skipped, try PYRO directly on specific host
        host = Pyro4.config.NS_HOST
        port = Pyro4.config.NS_PORT
    # pyro direct lookup
    if not port:
        port = Pyro4.config.NS_PORT
    if ":" in host:
        host = "[%s]" % host
    if core.URI.isUnixsockLocation(host):
        uristring = "PYRO:%s@%s" % (Pyro4.constants.NAMESERVER_NAME, host)
    else:
        uristring = "PYRO:%s@%s:%d" % (Pyro4.constants.NAMESERVER_NAME, host, port)
    uri = core.URI(uristring)
    log.debug("locating the NS: %s", uri)
    proxy = core.Proxy(uri)
    proxy._pyroHmacKey = hmac_key
    try:
        proxy.ping()
        log.debug("located NS")
        return proxy
    except PyroError as x:
        e = NamingError("Failed to locate the nameserver")
        e.__cause__ = x
        raise e


def resolve(uri, hmac_key=None):
    """Resolve a 'magic' uri (PYRONAME) into the direct PYRO uri."""
    if isinstance(uri, basestring):
        uri = core.URI(uri)
    elif not isinstance(uri, core.URI):
        raise TypeError("can only resolve Pyro URIs")
    if uri.protocol == "PYRO":
        return uri
    log.debug("resolving %s", uri)
    if uri.protocol == "PYRONAME":
        nameserver = locateNS(uri.host, uri.port, hmac_key=hmac_key)
        uri = nameserver.lookup(uri.object)
        nameserver._pyroRelease()
        return uri
    else:
        raise PyroError("invalid uri protocol")


def main(args=None):
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-n", "--host", dest="host", help="hostname to bind server on")
    parser.add_option("-p", "--port", dest="port", type="int", help="port to bind server on (0=random)")
    parser.add_option("-u", "--unixsocket", help="Unix domain socket name to bind server on")
    parser.add_option("-s", "--storage", help="Storage system to use (memory, dbm:file, sql:file)", default="memory")
    parser.add_option("", "--bchost", dest="bchost", help="hostname to bind broadcast server on (default is \"\")")
    parser.add_option("", "--bcport", dest="bcport", type="int",
                      help="port to bind broadcast server on (0=random)")
    parser.add_option("", "--nathost", dest="nathost", help="external hostname in case of NAT")
    parser.add_option("", "--natport", dest="natport", type="int", help="external port in case of NAT")
    parser.add_option("-x", "--nobc", dest="enablebc", action="store_false", default=True,
                      help="don't start a broadcast server")
    parser.add_option("-k", "--key", help="the HMAC key to use")
    options, args = parser.parse_args(args)
    startNSloop(options.host, options.port, enableBroadcast=options.enablebc,
                bchost=options.bchost, bcport=options.bcport, unixsocket=options.unixsocket,
                nathost=options.nathost, natport=options.natport, storage=options.storage,
                hmac=options.key)


if __name__ == "__main__":
    main()
