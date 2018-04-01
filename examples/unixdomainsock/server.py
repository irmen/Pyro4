from __future__ import print_function
import os

import Pyro4


@Pyro4.expose
class Thingy(object):
    def message(self, arg):
        print("Message received:", arg)
        return "Roger!"


if os.path.exists("example_unix.sock"):
    os.remove("example_unix.sock")

with Pyro4.Daemon(unixsocket="example_unix.sock") as d:
    uri = d.register(Thingy, "example.unixsock")
    print("Server running, uri=", uri)
    d.requestLoop()
