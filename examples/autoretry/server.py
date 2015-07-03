from __future__ import print_function
import time

import Pyro4


class CalcServer(object):
    def add(self, num1, num2):
        print("calling add: %d, %d" % (num1, num2))
        return num1 + num2


Pyro4.config.COMMTIMEOUT = 0.5  # the server will very likely timed-out

ns = Pyro4.naming.locateNS()
daemon = Pyro4.core.Daemon()
obj = CalcServer()
uri = daemon.register(obj)
ns.register("example.autoretry", uri)
print("Server ready.")
daemon.requestLoop()
