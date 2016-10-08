from __future__ import print_function, division
import time
import Pyro4


if Pyro4.config.STREAMING:
    print("Note: Streaming has been enabled in the Pyro config.")
else:
    print("Note: Streaming has not been enabled in the Pyro config (PYRO_STREAMING).")


@Pyro4.expose
class Streamer(object):
    def list(self):
        return [1, 2, 3, 4, 5, 6, 7, 8, 9]

    def iterator(self):
        return iter([1, 2, 3, 4, 5, 6, 7, 8, 9])

    def generator(self):
        i = 1
        while i < 10:
            yield i
            i += 1

    def slow_generator(self):
        i = 1
        while i < 10:
            yield i
            time.sleep(0.5)
            i += 1


Pyro4.Daemon.serveSimple({
        Streamer: "example.streamer"
    }, ns=False)
