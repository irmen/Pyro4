from __future__ import print_function
import Pyro4
from messagebus.messagebus import Subscriber
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


if len(sys.argv) != 2:
    raise SystemExit("give hostname to bind on as argument")

subber = Subber()
d = Pyro4.Daemon(host=sys.argv[1].strip())
d.register(subber)

subber.bus.subscribe("weather-forecast", subber)
# note: we subscribe on the bus *after* registering the subber as a Pyro object
# this results in Pyro automatically making a proxy for the subber
print("Subscribed on weather-forecast")
d.requestLoop()
