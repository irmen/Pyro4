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

    @Pyro4.expose
    def download_chunks(self, size):
        print("client requests a 'streaming' download of %d bytes" % size)
        data = bytearray(size)
        i = 0
        chunksize = 200000
        print("  using chunks of size", chunksize)
        while i < size:
            yield data[i:i+chunksize]
            i += chunksize


Pyro4.Daemon.serveSimple(
    {
        Testclass: "example.hugetransfer"
    },
    host=Pyro4.socketutil.getIpAddress("localhost", workaround127=True),
    ns=False, verbose=True)
