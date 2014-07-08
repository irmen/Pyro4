from __future__ import print_function
import Pyro4

from thingy import Thingy


class Factory(object):
    def createSomething(self, number):
        # create a new item
        thing = Thingy(number)
        # connect it to the Pyro daemon to make it a Pyro object
        self._pyroDaemon.register(thing)
        # Return it. Pyro's autoproxy feature turns it into a proxy automatically.
        # If that feature is disabled, the object itself (a copy) is returned,
        # and the client won't be able to interact with the actual Pyro object here.
        return thing


d = Pyro4.Daemon()
uri = d.register(Factory(), "example.autoproxy")
print("server object uri:", uri)
print("autoproxy?", Pyro4.config.AUTOPROXY)
print("factory server running.")
d.requestLoop()
