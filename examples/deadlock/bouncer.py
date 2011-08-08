from __future__ import print_function, with_statement
import Pyro4.threadutil

# a message bouncer. Passes messages back to the callback
# object, until a certain limit is reached.

class Bouncer(object):
    def __init__(self, name):
        self.name = name
        self.count = 0
        self.callbackMutex = Pyro4.threadutil.Lock()

    def register(self, callback):
        self.callback = callback

    def process(self, message):
        print("in process", self.name)
        if len(message) >= 3:
            print("Back in", self.name, ", message is large enough... stopping!")
            return ["complete at " + self.name + ":" + str(self.count)]

        print("I'm", self.name, ", bouncing back...")
        message.append(self.name)
        with self.callbackMutex:
            result = self.callback.process(message)
        self.count += 1
        result.insert(0, "passed on from " + self.name + ":" + str(self.count))
        print("returned from callback")
        return result
