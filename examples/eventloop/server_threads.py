from __future__ import print_function
import socket
import select
import time

import Pyro4.core
import Pyro4.naming
import Pyro4.socketutil

Pyro4.config.SERVERTYPE = "thread"


hostname = socket.gethostname()
my_ip = Pyro4.socketutil.getIpAddress(None, workaround127=True)


@Pyro4.expose
class EmbeddedServer(object):
    def multiply(self, x, y):
        return x * y


print("THREADED server type. Initializing services...")
print("Make sure that you don't have a name server running already!\n")
# start a name server with broadcast server
nameserverUri, nameserverDaemon, broadcastServer = Pyro4.naming.startNS(host=my_ip)
assert broadcastServer is not None, "expect a broadcast server to be created"
print("got a Nameserver, uri=%s" % nameserverUri)

# create a Pyro daemon
pyrodaemon = Pyro4.core.Daemon(host=hostname)
serveruri = pyrodaemon.register(EmbeddedServer())
print("server uri=%s" % serveruri)

# register it with the embedded nameserver
nameserverDaemon.nameserver.register("example.embedded.server", serveruri)

print("")

# Below is our custom event loop.
# Because this particular server runs the different daemons using the "tread" server type,
# there is no built in way of combining the different event loops and server sockets.
# We have to write our own multiplexing server event loop, and dispatch the requests
# to the server that they belong to.
# It is a bit silly to do it this way because the choice for a threaded server type
# has already been made-- so you could just as well run the different daemons' request loops
# each in their own thread and avoid writing this integrated event loop altogether.
# But for the sake of example we write out our own loop:

try:
    while True:
        print(time.asctime(), "Waiting for requests...")
        # create sets of the socket objects we will be waiting on
        # (a set provides fast lookup compared to a list)
        nameserverSockets = set(nameserverDaemon.sockets)
        pyroSockets = set(pyrodaemon.sockets)
        rs = [broadcastServer]  # only the broadcast server is directly usable as a select() object
        rs.extend(nameserverSockets)
        rs.extend(pyroSockets)
        rs, _, _ = select.select(rs, [], [], 3)
        eventsForNameserver = []
        eventsForDaemon = []
        for s in rs:
            if s is broadcastServer:
                print("Broadcast server received a request")
                broadcastServer.processRequest()
            elif s in nameserverSockets:
                eventsForNameserver.append(s)
            elif s in pyroSockets:
                eventsForDaemon.append(s)
        if eventsForNameserver:
            print("Nameserver received a request")
            nameserverDaemon.events(eventsForNameserver)
        if eventsForDaemon:
            print("Daemon received a request")
            pyrodaemon.events(eventsForDaemon)
except KeyboardInterrupt:
    pass

nameserverDaemon.close()
broadcastServer.close()
pyrodaemon.close()
print("done")
