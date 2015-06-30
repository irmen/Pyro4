from __future__ import print_function
from time import sleep
import sys

import Pyro4
import Pyro4.errors


# client side will not have timeout
Pyro4.config.COMMTIMEOUT = 0

# Not using auto-retry feature
Pyro4.config.MAX_RETRIES = 0

obj = Pyro4.core.Proxy("PYRONAME:example.autoretry")
print("Calling remote function 1st time (create connection)")
obj.add(1, 1)
print("Calling remote function 2nd time (not timed out yet)")
obj.add(2, 2)
print("Sleeping 1 second...")
sleep(1)
print("Calling remote function 3rd time (will raise an exception)")
try:
    obj.add(3, 3)
except Exception as e:
    print("Got exception %r as expected." % repr(e))

print("Now, let's enable the auto retry")
obj._pyroRelease()
obj._pyroMaxRetries = 2

print("Calling remote function 1st time (create connection)")
obj.add(1, 1)
print("Calling remote function 2nd time (not timed out yet)")
obj.add(2, 2)
print("Sleeping 1 second...")
sleep(1)
print("Calling remote function 3rd time (will not raise any exceptions)")
obj.add(3, 3)
