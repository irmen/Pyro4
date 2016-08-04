from __future__ import print_function
import Pyro4


# a Chain member. Passes messages to the next link,
# until the message went full-circle: then it exits.

class Chain(object):
    def __init__(self, name, next_node):
        self.name = name
        self.nextName = next_node
        self.next = None

    @Pyro4.expose
    def process(self, message):
        if self.next is None:
            self.next = Pyro4.core.Proxy("PYRONAME:example.chain." + self.nextName)
        if self.name in message:
            print("Back at %s; we completed the circle!" % self.name)
            return ["complete at " + self.name]
        else:
            print("I'm %s, passing to %s" % (self.name, self.nextName))
            message.append(self.name)
            result = self.next.process(message)
            result.insert(0, "passed on from " + self.name)
            return result
