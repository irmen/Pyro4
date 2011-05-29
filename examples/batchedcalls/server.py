from __future__ import print_function
import Pyro4
from Pyro4.socketutil import getMyIpAddress

class Thingy(object):
    def multiply(self,a,b):
        return a*b
    def add(self,a,b):
        return a+b
    def divide(self,a,b):
        return a//b
    def error(self):
        return 1//0

d=Pyro4.Daemon(host=getMyIpAddress(workaround127=True), port=0)
uri=d.register(Thingy())
print("server object uri:",uri)
print("server running.")
d.requestLoop()
