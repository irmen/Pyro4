import Pyro4
from messagebus import Subscriber
from Pyro4.util import excepthook
import sys

sys.excepthook = excepthook

Pyro4.config.AUTOPROXY = True


@Pyro4.expose()
class Subber(Subscriber):
    def consume_message(self, topic, msgid, seq, created, data):
        print("\nGOT MESSAGE:")
        print("   topic:", topic, type(topic))
        print("   msgid:", msgid, type(msgid))
        print(" created:", created, type(created))
        print("     seq:", seq, type(seq))
        print("    data:", data, type(data))


subber = Subber()
d = Pyro4.Daemon()
d.register(subber)

subber.bus.subscribe("weather-forecast", subber)
# note: we subscribe on the bus *after* registering the subber as a Pyro object
# this results in Pyro automatically making a proxy for the subber
print("Subscribed on weather-forecast")
d.requestLoop()
