from __future__ import print_function
import time

import Pyro4


# set the oneway behavior to run inside a new thread, otherwise the client stalls.
# this is the default, but I've added it here just for clarification.
Pyro4.config.ONEWAY_THREADED = True


class Server(object):
    def __init__(self):
        self.busy = False

    @Pyro4.oneway
    def oneway_start(self, duration):
        print("start request received. Starting work...")
        self.busy = True
        for i in range(duration):
            time.sleep(1)
            print(duration - i)
        print("work is done!")
        self.busy = False

    def ready(self):
        print("ready status requested (%r)" % (not self.busy))
        return not self.busy

    def result(self):
        return "The result :)"

    def nothing(self):
        print("nothing got called, doing nothing")

    @Pyro4.oneway
    def oneway_work(self):
        for i in range(10):
            print("work work..", i+1)
            time.sleep(1)
        print("work's done!")


# main program

Pyro4.Daemon.serveSimple({
    Server(): "example.oneway"
})
