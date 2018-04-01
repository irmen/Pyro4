from __future__ import print_function
import time
import sys

import Pyro4
import Pyro4.errors


# NOTE: the timer in IronPython seems to be wacky.
# So we use wider margins for that, to check if the delays are ok.

def approxEqual(x, y):
    return abs(x - y) < 0.2

# disable timeout globally
Pyro4.config.COMMTIMEOUT = 0

obj = Pyro4.core.Proxy("PYRONAME:example.timeout")
obj._pyroBind()
print("No timeout is configured. Calling delay with 2 seconds.")
start = time.time()
result = obj.delay(2)
assert result == "slept 2 seconds"
duration = time.time() - start
if sys.platform != "cli":
    assert approxEqual(duration, 2), "expected 2 seconds duration"
else:
    assert 1.0 < duration < 3.0, "expected about 2 seconds duration"

# override timeout for this object
obj._pyroTimeout = 1
print("Timeout set to 1 seconds. Calling delay with 2 seconds.")
start = time.time()
try:
    result = obj.delay(2)
    print("!?should have raised TimeoutError!?")
except Pyro4.errors.TimeoutError:
    print("TimeoutError! As expected!")
    duration = time.time() - start
    if sys.platform != "cli":
        assert approxEqual(duration, 1), "expected 1 seconds duration"
    else:
        assert 0.9 < duration < 1.9, "expected about 1 second duration"

# set timeout globally
Pyro4.config.COMMTIMEOUT = 1

obj = Pyro4.core.Proxy("PYRONAME:example.timeout")
print("COMMTIMEOUT is set globally. Calling delay with 2 seconds.")
start = time.time()
try:
    result = obj.delay(2)
    print("!?should have raised TimeoutError!?")
except Pyro4.errors.TimeoutError:
    print("TimeoutError! As expected!")
    duration = time.time() - start
    if sys.platform != "cli":
        assert approxEqual(duration, 1), "expected 1 seconds duration"
    else:
        assert 0.9 < duration < 1.9, "expected about 1 second duration"

# override again for this object
obj._pyroTimeout = None
print("No timeout is configured. Calling delay with 3 seconds.")
start = time.time()
result = obj.delay(3)
assert result == "slept 3 seconds"
duration = time.time() - start
if sys.platform != "cli":
    assert approxEqual(duration, 3), "expected 3 seconds duration"
else:
    assert 2.5 < duration < 3.5, "expected about 3 second duration"

print("Trying to connect to the frozen daemon.")
obj = Pyro4.core.Proxy("PYRONAME:example.timeout.frozendaemon")
obj._pyroTimeout = 1
print("Timeout set to 1 seconds. Trying to connect.")
start = time.time()
try:
    result = obj.delay(5)
    print("!?should have raised TimeoutError!?")
except Pyro4.errors.TimeoutError:
    print("TimeoutError! As expected!")
    duration = time.time() - start
    if sys.platform != "cli":
        assert approxEqual(duration, 1), "expected 1 seconds duration"
    else:
        assert 0.9 < duration < 1.9, "expected about 1 second duration"

print("Disabling timeout and trying to connect again. This may take forever now.")
print("Feel free to abort with ctrl-c or ctrl-break.")
obj._pyroTimeout = None
obj.delay(1)
