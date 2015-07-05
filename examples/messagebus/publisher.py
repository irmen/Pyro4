from __future__ import print_function
import time
import random
import sys
import Pyro4
import Pyro4.errors
from Pyro4.util import excepthook
from messagebus import PYRO_MSGBUS_NAME

sys.excepthook = excepthook


if len(sys.argv) != 2:
    raise SystemExit("please give a city or country name as argument.")
location = sys.argv[1].strip()

bus = Pyro4.Proxy("PYRONAME:"+PYRO_MSGBUS_NAME)

while True:
    time.sleep(0.01)
    forecast = (location, random.choice(["sunny", "cloudy", "storm", "rainy", "hail", "thunder", "calm", "mist", "cold", "hot"]))
    print("Forecast:", forecast)
    try:
        bus.send("weather-forecast", forecast)
    except Pyro4.errors.CommunicationError:
        print("connection to the messagebus is lost, reconnecting...")
        bus._pyroReconnect()
