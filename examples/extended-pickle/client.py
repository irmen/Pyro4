from __future__ import print_function
import sys
import Pyro4

if sys.version_info < (3, 0):
    input = raw_input

Pyro4.config.SERIALIZER = "cloudpickle"   # can also use "dill"

uri = input("Uri of extended-pickle example server? ").strip()


class WorkerThing(object):
    def __init__(self, name):
        self.name = name

    def __call__(self, servername):
        return "this is the result of object %s on server %s" % (self.name, servername)


def somework(servername):
    return "this is the result of function somework on server %s" % servername


with Pyro4.core.Proxy(uri) as p:
    print("sending a callable object to the server:")
    print("  ", p.work(WorkerThing("peter")))
    print("sending a function to the server:")
    print("  ", p.work(somework))
    print("sending a lambda to the server:")
    print("  ", p.work(lambda servername: "this is the result of the lambda function on server %s" % servername))
