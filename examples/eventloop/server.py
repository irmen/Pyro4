#!/usr/bin/env python
import socket
import time
import select
import sys
import Pyro.core
import Pyro.naming

if sys.version_info<(3,0):
    input=raw_input

servertype=input("Servertype thread/select (t/s)?")
if servertype=='t':
    Pyro.config.SERVERTYPE="thread"
else:
    Pyro.config.SERVERTYPE="select"

hostname=socket.gethostname()

class EmbeddedServer(object):
    def multiply(self, x, y):
        return x*y


print("initializing services... servertype=%s" % Pyro.config.SERVERTYPE)
# start a name server with broadcast server as well
nameserverUri, nameserverDaemon, broadcastServer = Pyro.naming.startNS(host=hostname)
assert broadcastServer is not None, "expect a broadcast server to be created"

print("got a Nameserver, uri=%s" % nameserverUri)
print("ns daemon location string=%s" % nameserverDaemon.locationStr)
print("ns daemon socket=%s (fileno %d)" % (nameserverDaemon.sock, nameserverDaemon.fileno()))
print("bc server socket=%s (fileno %d)" % (broadcastServer.sock, broadcastServer.fileno()))

# create a Pyro daemon
pyrodaemon=Pyro.core.Daemon(host=hostname)
print("daemon location string=%s" % pyrodaemon.locationStr)
print("daemon socket=%s (fileno %d)" % (pyrodaemon.sock, pyrodaemon.fileno()))

# register a server object with the daemon
serveruri=pyrodaemon.register(EmbeddedServer())
print("server uri=%s" % serveruri)

# register it with the embedded nameserver directly
nameserverDaemon.nameserver.register("example.embedded.server",serveruri)

print("")

# below is our custom event loop.
while True:
    print("Waiting for events...")
    rs=[nameserverDaemon, broadcastServer, pyrodaemon]
    rs,_,_ = select.select(rs,[],[],3)          # use select on the three pyro objects to multiplex them
    if broadcastServer in rs:
        print("Broadcast server received a request")
        broadcastServer.processRequest()
    if nameserverDaemon in rs:
        print("Nameserver received a request")
        nameserverDaemon.handleRequests()
    if pyrodaemon in rs:
        print("Daemon received a request")
        pyrodaemon.handleRequests()

nameserverDaemon.close()
broadcastServer.close()
pyrodaemon.close()
print("done")
