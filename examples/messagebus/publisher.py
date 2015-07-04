import time
import random
import Pyro4
import Pyro4.errors
from messagebus import PYRO_MSGBUS_NAME


bus = Pyro4.Proxy("PYRONAME:"+PYRO_MSGBUS_NAME)

while True:
    time.sleep(0.5)
    forecast = random.choice(["sunny", "cloudy", "storm", "rainy", "hail", "thunder", "calm", "mist", "cold", "hot"])
    print("Forecast:", forecast)
    try:
        bus.send("weather-forecast", forecast)
    except Pyro4.errors.ConnectionClosedError:
        print("connection to the messagebus is lost, reconnecting...")
        bus._pyroReconnect()
