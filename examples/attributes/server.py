from __future__ import print_function
import Pyro4


something = "Something"


class SubThingy(object):
    def __init__(self):
        self.value = 42
        self._value = 123
        self.__value = 999

    def getValue(self):
        return self.value

    def addToValue(self, amount):
        self.value += amount


class Thingy(object):
    def __init__(self):
        self.sub = SubThingy()
        self.value = 42
        self._value = 123
        self.__value = 999

    @Pyro4.expose
    def __dunder__(self):
        return "yep"

    @Pyro4.expose
    def __len__(self):
        return 200

    def getSubValue(self):
        return self.sub.getValue()

    def addSubValue(self, amount):
        self.sub.addToValue(amount)

    def printSomething(self):
        print("something:", something)
        return something

    def getValue(self):
        return self.value

    @Pyro4.expose
    @property
    def prop_value(self):
        return self.value

    @Pyro4.expose
    @prop_value.setter
    def prop_value(self, value):
        self.value = value

    @Pyro4.expose
    @property
    def prop_sub(self):
        return self.sub


d = Pyro4.Daemon()
uri = d.register(Thingy(), "example.attributes")
print("server object uri:", uri)
print("attributes server running.")
d.requestLoop()
