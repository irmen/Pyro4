import Pyro4
import excep

Pyro4.Daemon.serveSimple(
    {
        excep.TestClass: "example.exceptions"
    },
    ns=True, verbose=True)
