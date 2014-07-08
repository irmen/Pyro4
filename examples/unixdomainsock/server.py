from __future__ import print_function
import os

import Pyro4


class Thingy(object):
    def message(self, arg):
        print("Message received:", arg)
        return "Roger!"


if os.path.exists("example_unix.sock"):
    os.remove("example_unix.sock")
d = Pyro4.Daemon(unixsocket="example_unix.sock")
uri = d.register(Thingy(), "example.unixsock")
print("Server running, uri=", uri)
d.requestLoop()
