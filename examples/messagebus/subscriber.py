"""
This is a subscriber meant for the 'weather' messages example.
It uses a callback to process incoming messages.
"""
from __future__ import print_function
import sys
import Pyro4
from messagebus.messagebus import Subscriber
from Pyro4.util import excepthook

sys.excepthook = excepthook
if sys.version_info < (3, 0):
    input = raw_input

Pyro4.config.AUTOPROXY = True


@Pyro4.expose
class Subber(Subscriber):
    def consume_message(self, topic, message):
        # This callback-method is called automatically when a message arrives on the bus.
        print("\nGOT MESSAGE:")
        print("   topic:", topic)
        print("   msgid:", message.msgid)
        print(" created:", message.created)
        print("    data:", message.data)


hostname = input("hostname to bind on (empty=localhost): ").strip() or "localhost"

# create a messagebus subscriber that uses automatic message retrieval (via a callback)
subber = Subber()
d = Pyro4.Daemon(host=hostname)
d.register(subber)

topics = subber.bus.topics()
print("Topics on the bus: ", topics)
print("Subscribing to weather-forecast.")

subber.bus.subscribe("weather-forecast", subber)
# note: we subscribe on the bus *after* registering the subber as a Pyro object
# this results in Pyro automatically making a proxy for the subber
print("Subscribed on weather-forecast")
d.requestLoop()
