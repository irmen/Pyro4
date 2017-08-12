from __future__ import print_function
import Pyro4


class Server(object):
    @Pyro4.expose
    def work(self, callable):
        print("RECEIVED WORK:", callable)
        result = callable("ExtendedPickle")     # perform the work!
        print("    result:", result)
        return result


Pyro4.config.SERIALIZERS_ACCEPTED.add("cloudpickle")
Pyro4.config.SERIALIZERS_ACCEPTED.add("dill")

Pyro4.Daemon.serveSimple(
    {
        Server: "example.extended-pickle"
    },
    ns=False, verbose=True)
