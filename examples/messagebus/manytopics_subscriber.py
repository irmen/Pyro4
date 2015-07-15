"""
This is the subscriber for the 'many topics' messages example.
For code with more explanations, see the regular 'weather' message example code.
"""
from __future__ import print_function
import sys
import Pyro4
from messagebus.messagebus import Subscriber
from Pyro4.util import excepthook

sys.excepthook = excepthook

Pyro4.config.AUTOPROXY = True


@Pyro4.expose()
class Subber(Subscriber):
    def consume_message(self, topic, message):
        print("\nGOT MESSAGE:")
        print("   topic:", topic)
        print("   msgid:", message.msgid)
        print(" created:", message.created)
        print("    data:", message.data)


subber = Subber()
d = Pyro4.Daemon()
d.register(subber)

topics = ["msg.topic.%s" % letter for letter in "abcdefghijklmnopqrstuvwxyz"]
subber.bus.subscribe(subber, *topics)  # mass subscribe

topics = subber.bus.topics()
print("Topics on the bus: ", topics)
print("Receiving messages!")
d.requestLoop()
