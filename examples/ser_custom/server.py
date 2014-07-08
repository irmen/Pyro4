from __future__ import print_function
import Pyro4
from Pyro4.util import SerializerBase
import mycustomclasses

# use serpent
Pyro4.config.SERIALIZER = "serpent"


# register the special serialization hooks
def thingy_class_to_dict(obj):
    print("{serializer hook, converting to dict: %s}" % obj)
    return {
        "__class__": "waheeee-custom-thingy",
        "number-attribute": obj.number
    }


def thingy_dict_to_class(classname, d):
    print("{deserializer hook, converting to class: %s}" % d)
    return mycustomclasses.Thingy(d["number-attribute"])


def otherthingy_dict_to_class(classname, d):
    print("{deserializer hook, converting to class: %s}" % d)
    return mycustomclasses.OtherThingy(d["number"])

# for 'Thingy' we register both serialization and deserialization hooks
SerializerBase.register_dict_to_class("waheeee-custom-thingy", thingy_dict_to_class)
SerializerBase.register_class_to_dict(mycustomclasses.Thingy, thingy_class_to_dict)

# for 'OtherThingy' we only register a deserialization hook (and for serialization depend on serpent's default behavior)
SerializerBase.register_dict_to_class("mycustomclasses.OtherThingy", otherthingy_dict_to_class)


# regular Pyro server stuff

class Server(object):
    def method(self, arg):
        print("\nmethod called, arg=", arg)
        response = mycustomclasses.Thingy(999)
        return response

    def othermethod(self, arg):
        print("\nothermethod called, arg=", arg)
        response = mycustomclasses.OtherThingy(999)
        return response


Pyro4.core.Daemon.serveSimple(
    {
        Server(): "example.customclasses"
    },
    ns=False)
