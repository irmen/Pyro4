from __future__ import print_function

import Pyro4
import Pyro4.socketutil
import serpent


# Pyro4.config.COMMTIMEOUT=2


class Testclass(object):
    @Pyro4.expose
    def transfer(self, data):
        if Pyro4.config.SERIALIZER == "serpent" and type(data) is dict:
            data = serpent.tobytes(data)  # in case of serpent encoded bytes
        print("received %d bytes" % len(data))
        return len(data)


Pyro4.Daemon.serveSimple(
    {
        Testclass: "example.hugetransfer"
    },
    host=Pyro4.socketutil.getIpAddress("localhost", workaround127=True),
    ns=False, verbose=True)
