from __future__ import print_function
import base64

import Pyro4
import Pyro4.socketutil


# Pyro4.config.COMMTIMEOUT=2


class Testclass(object):
    def transfer(self, data):
        if Pyro4.config.SERIALIZER == "serpent" and type(data) is dict:
            # decode serpent base-64 encoded bytes
            assert data["encoding"] == "base64"
            data = base64.b64decode(data["data"])
        print("received %d bytes" % len(data))
        return len(data)


Pyro4.Daemon.serveSimple(
    {
        Testclass(): "example.hugetransfer"
    },
    host=Pyro4.socketutil.getIpAddress("localhost", workaround127=True),
    ns=False, verbose=True)
