import time
import Pyro4


class Worker(object):
    def __init__(self, number, callback):
        self.number = number
        self.callback = callback
        print("Worker %d created" % self.number)

    @Pyro4.expose
    @Pyro4.oneway
    def work(self, amount):
        print("Worker %d busy..." % self.number)
        time.sleep(amount)
        print("Worker %d done. Informing callback client." % self.number)
        self._pyroDaemon.unregister(self)
        self.callback.done(self.number)  # invoke the callback object


class CallbackServer(object):
    def __init__(self):
        self.number = 0

    @Pyro4.expose
    def addworker(self, callback):
        self.number += 1
        print("server: adding worker %d" % self.number)
        worker = Worker(self.number, callback)
        self._pyroDaemon.register(worker)  # make it a Pyro object
        return worker


Pyro4.Daemon.serveSimple({
    CallbackServer: "example.callback"
})
