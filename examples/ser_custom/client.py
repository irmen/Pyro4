from __future__ import print_function
import sys
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


# regular pyro stuff

if sys.version_info<(3,0):
    input=raw_input

uri = input("Enter the URI of the server object: ")
serv = Pyro4.core.Proxy(uri)
print("Transferring object...")
o = mycustomclasses.Thingy(42)
response = serv.method(o)
print("type of response object:", type(response))
print("response:", response)
