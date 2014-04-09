from __future__ import print_function
import Pyro4
from Pyro4.util import SerializerBase
import mycustomclasses

# use serpent
Pyro4.config.SERIALIZER = "serpent"

# register the special serialization hooks

def thingy_dict_to_class(classname, d):
    print("{deserializer hook, converting to class: %s}" % d)
    return mycustomclasses.Thingy(d["number-attribute"])

def thingy_class_to_dict(obj):
    print("{serializer hook, converting to dict: %s}" % obj)
    return {
        "__class__": "waheeee-custom-thingy",
        "number-attribute": obj.number
    }

SerializerBase.register_dict_to_class("waheeee-custom-thingy", thingy_dict_to_class)
SerializerBase.register_class_to_dict(mycustomclasses.Thingy, thingy_class_to_dict)


# regular Pyro server stuff

class Server(object):
    def method(self, arg):
        print("method called, arg=", arg)
        response = mycustomclasses.Thingy(999)
        return response


Pyro4.core.Daemon.serveSimple(
    {
        Server(): "example.customclasses"
    },
    ns=False)
