import Pyro4


class CallbackServer(object):
    @Pyro4.expose
    @Pyro4.oneway
    def doCallback(self, callback):
        print("\n\nserver: doing callback 1 to client")
        try:
            callback.call1()
        except:
            print("got an exception from the callback:")
            print("".join(Pyro4.util.getPyroTraceback()))
        print("\n\nserver: doing callback 2 to client")
        try:
            callback.call2()
        except:
            print("got an exception from the callback:")
            print("".join(Pyro4.util.getPyroTraceback()))
        print("server: callbacks done.\n")


Pyro4.Daemon.serveSimple({
    CallbackServer: "example.callback2"
})
