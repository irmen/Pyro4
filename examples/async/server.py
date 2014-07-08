from __future__ import print_function
import time

import Pyro4


class Thingy(object):
    def divide(self, a, b):
        print("dividing {0} by {1} after a slight delay".format(a, b))
        time.sleep(3)
        return a // b

    def multiply(self, a, b):
        print("multiply {0} by {1}, no delay".format(a, b))
        return a * b

    def add(self, value, increase):
        print("adding {1} to {0}, no delay".format(value, increase))
        return value + increase


d = Pyro4.Daemon()
uri = d.register(Thingy(), "example.async")
print("server object uri:", uri)
print("async server running.")
d.requestLoop()
