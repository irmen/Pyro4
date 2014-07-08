from __future__ import print_function
import logging

import Pyro4


logging.basicConfig(level=logging.DEBUG)
logging.getLogger("Pyro4").setLevel(logging.DEBUG)

Pyro4.config.COMMTIMEOUT = 5.0
Pyro4.config.POLLTIMEOUT = 5.0  # only used for multiplexing server


class TestDisconnect(object):
    def echo(self, arg):
        print("echo: ", arg)
        return arg


d = Pyro4.Daemon()
uri = d.register(TestDisconnect(), "disconnect")
print("uri =", uri)
d.requestLoop()
