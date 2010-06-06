import time
import Pyro

class TimeoutServer(object):
    def delay(self, amount):
        print "sleeping",amount
        time.sleep(amount)
        print "done."
        return "slept %d seconds" % amount

Pyro.config.COMMTIMEOUT=0        # the server won't be using timeouts

ns=Pyro.naming.locateNS()
daemon=Pyro.core.Daemon()
daemon2=Pyro.core.Daemon()
obj=TimeoutServer()
obj2=TimeoutServer()
uri=daemon.register(obj)
uri2=daemon2.register(obj2)
ns.remove("example.timeout")
ns.remove("example.timeout.frozendaemon")
ns.register("example.timeout",uri)
ns.register("example.timeout.frozendaemon",uri2)
print "Server ready."
# Note that we're only starting one of the 2 daemons.
# daemon2 is not started to simulate connection timeouts.
daemon.requestLoop()
