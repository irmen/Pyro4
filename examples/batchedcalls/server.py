from __future__ import print_function
import time

import Pyro4
from Pyro4.socketutil import getIpAddress


class Thingy(object):
    def multiply(self, a, b):
        return a * b

    def add(self, a, b):
        return a + b

    def divide(self, a, b):
        return a // b

    def error(self):
        return 1 // 0

    def delay(self, seconds):
        time.sleep(seconds)
        return seconds

    def printmessage(self, message):
        print(message)
        return 0


d = Pyro4.Daemon(host=getIpAddress("", workaround127=True), port=0)
uri = d.register(Thingy(), "example.batched")
print("server object uri:", uri)
print("batched calls server running.")
d.requestLoop()
