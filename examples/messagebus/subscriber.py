import Pyro4
from messagebus.client import Subscriber
from Pyro4.util import excepthook
import sys

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

subber.bus.subscribe("weather-forecast", subber)
# note: we subscribe on the bus *after* registering the subber as a Pyro object
# this results in Pyro automatically making a proxy for the subber
print("Subscribed on weather-forecast")
d.requestLoop()
