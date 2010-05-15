import Pyro.core
import time
from Pyro.errors import TimeoutError

def approxEqual(x,y):
    return abs(x-y) < 0.1

# disable timeout globally 
Pyro.config.COMMTIMEOUT=None

obj=Pyro.core.Proxy("PYRONAME:example.timeout")
print "No timeout is configured. Calling delay with 2 seconds."
start=time.time()
result=obj.delay(2)
assert result=="slept 2 seconds"
duration=time.time()-start
assert approxEqual(duration,2), "expected 2 seconds duration"

# override timeout for this object
obj._pyroTimeout=1
print "Timeout set to 1 seconds. Calling delay with 2 seconds."
start=time.time()
try:
    result=obj.delay(2)
    print "!?should have raised TimeoutError!?"
except TimeoutError:
    print "Timeouterror! As expected!"
    duration=time.time()-start
    assert approxEqual(duration,1), "expected 1 seconds duration"

# set timeout globally
Pyro.config.COMMTIMEOUT=1

obj=Pyro.core.Proxy("PYRONAME:example.timeout")
print "COMMTIMEOUT is set globally. Calling delay with 2 seconds."
start=time.time()
try:
    result=obj.delay(2)
    print "!?should have raised TimeoutError!?"
except TimeoutError:
    print "Timeouterror! As expected!"
    duration=time.time()-start
    assert approxEqual(duration,1), "expected 1 seconds duration"

# override again for this object
obj._pyroTimeout=None
print "No timeout is configured. Calling delay with 3 seconds."
start=time.time()
result=obj.delay(3)
assert result=="slept 3 seconds"
duration=time.time()-start
assert approxEqual(duration,3), "expected 3 seconds duration"

print 
print "Trying to connect to the frozen daemon."
obj=Pyro.core.Proxy("PYRONAME:example.timeout.frozendaemon")
obj._pyroTimeout=1
print "Timeout set to 1 seconds. Trying to connect."
start=time.time()
try:
    result=obj.delay(5)
    print "!?should have raised TimeoutError!?"
except TimeoutError:    
    print "Timeouterror! As expected!"
    duration=time.time()-start
    assert approxEqual(duration,1), "expected 1 seconds duration"
print "Disabling timeout and trying to connect again. This may take forever now."
print "Feel free to abort with ctrl-c or ctrl-break."
obj._pyroTimeout=None
obj.delay(1)
