from __future__ import print_function
import Pyro4

from thingy import Thingy


@Pyro4.expose
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


Pyro4.Daemon.serveSimple({
    Factory: "example.autoproxy"
}, ns=False)
