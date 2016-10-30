from __future__ import print_function, division
import time
import Pyro4


if Pyro4.config.ITER_STREAMING:
    print("Note: iter-streaming has been enabled in the Pyro config.")
else:
    print("Note: iter-streaming has not been enabled in the Pyro config (PYRO_ITER_STREAMING).")


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
            time.sleep(0.5)
            yield i
            i += 1

    def fibonacci(self):
        a, b = 0, 1
        while True:
            yield a
            a, b = b, a + b


Pyro4.Daemon.serveSimple({
        Streamer: "example.streamer"
    }, ns=False)
