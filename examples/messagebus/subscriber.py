import Pyro4
from messagebus import Subscriber

Pyro4.config.AUTOPROXY = True


@Pyro4.expose()
class Subber(Subscriber):
    @Pyro4.oneway
    def handle_message(self, topic, msgid, seq, created, data):
        print("\nGOT MESSAGE")
        print("   topic:", topic)
        print("   msgid:", msgid)
        print(" created:", created)
        print("     seq:", seq)
        print("    data:", data)


subber = Subber()
d = Pyro4.Daemon()
d.register(subber)

subber.bus.subscribe("weather-forecast", subber)
# note: we subscribe on the bus *after* registering the subber as a Pyro object
# this results in Pyro automatically making a proxy for the subber
print("Subscribed on weather-forecast")
d.requestLoop()
