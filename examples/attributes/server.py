from __future__ import print_function
import Pyro4

something = "Something"


@Pyro4.expose
class Thingy(object):
    def __init__(self):
        self.sub = {"name": "value"}
        self.value = 42
        self._value = 123
        self.__value = 999

    def __dunder__(self):
        return "yep"

    def __len__(self):
        return 200

    def getValue(self):
        return self.value

    @property
    def prop_value(self):
        return self.value

    @prop_value.setter
    def prop_value(self, value):
        self.value = value

    @property
    def prop_sub(self):
        return self.sub


Pyro4.Daemon.serveSimple({
    Thingy: "example.attributes"
}, ns=False)
