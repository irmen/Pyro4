import time
import random
import Pyro4
from messagebus import PYRO_MSGBUS_NAME


bus = Pyro4.Proxy("PYRONAME:"+PYRO_MSGBUS_NAME)
while True:
    time.sleep(0.5)
    forecast = random.choice(["sunny", "cloudy", "storm", "rainy", "hail", "thunder", "calm", "mist", "cold", "hot"])
    print("Forecast:", forecast)
    bus.send("weather-forecast", forecast)
