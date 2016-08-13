from __future__ import print_function

from awesome_thirdparty_library import AwesomeClass
import Pyro4


# expose the class from the library using @expose as wrapper function:
ExposedClass = Pyro4.expose(AwesomeClass)


with Pyro4.Daemon() as daemon:
    # register the wrapped class instead of the library class itself:
    uri = daemon.register(ExposedClass, "example.thirdpartylib")
    print("wrapped class registered, uri: ", uri)
    daemon.requestLoop()
