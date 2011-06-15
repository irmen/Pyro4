from __future__ import print_function
import sys
import Pyro4

if sys.version_info<(3,0):
    input=raw_input

dotted=input("enter value for DOTTEDNAMES config item: ").strip()
Pyro4.config.DOTTEDNAMES = dotted in ("1","true","on","yes")

something="Something"

class SubThingy(object):
    def __init__(self):
        self.value=42
        self._value=123
        self.__value=999
    def getValue(self):
        return self.value
    def setValue(self,value):
        self.value=value

class Thingy(object):
    def __init__(self):
        self.sub=SubThingy()
        self.value=42
        self._value=123
        self.__value=999
    def getSubValue(self):
        return self.sub.getValue()
    def setSubValue(self, value):
        self.sub.setValue(value)
    def dottedNames(self):
        return Pyro4.config.DOTTEDNAMES
    def printSomething(self):
        print("something:",something)
        return something

d=Pyro4.Daemon()
uri=d.register(Thingy(), "example.attributes")
print("server object uri:",uri)
print("DOTTEDNAMES=",Pyro4.config.DOTTEDNAMES)
print("attributes server running.")
d.requestLoop()
