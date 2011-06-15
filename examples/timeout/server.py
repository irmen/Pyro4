from __future__ import print_function
import time
import Pyro4


class TimeoutServer(object):
    def delay(self, amount):
        print("sleeping %d" % amount)
        time.sleep(amount)
        print("done.")
        return "slept %d seconds" % amount

Pyro4.config.COMMTIMEOUT=0        # the server won't be using timeouts

ns=Pyro4.naming.locateNS()
daemon=Pyro4.core.Daemon()
daemon2=Pyro4.core.Daemon()
obj=TimeoutServer()
obj2=TimeoutServer()
uri=daemon.register(obj)
uri2=daemon2.register(obj2)
ns.register("example.timeout",uri)
ns.register("example.timeout.frozendaemon",uri2)
print("Server ready.")
# Note that we're only starting one of the 2 daemons.
# daemon2 is not started to simulate connection timeouts.
daemon.requestLoop()
