from __future__ import print_function
import sys
import time
import Pyro4

if sys.version_info<(3,0):
    input=raw_input


def asyncFunction(value, increase=1):
    print(">>> async function called with value={0} increase={1}".format(value,increase))
    return value+increase

uri=input("enter async server object uri: ").strip()
proxy=Pyro4.Proxy(uri)

print("\n* async call with call chain:")
async=Pyro4.async(proxy)
asyncresult=async.divide(100,5)
# set a chain of callables to be invoked once the value is available
asyncresult.then(asyncFunction) \
           .then(asyncFunction) \
           .then(asyncFunction)
print("sleeping 4 seconds")
time.sleep(4)   # the call chain will be invoked during this sleep period
print("back from sleep")
# you can still access the final asyncresult.value. It should be 100/5+3=23
print("final value=",asyncresult.value)
assert asyncresult.value==23

print("\n* async call with call chain that is set 'too late':")
async=Pyro4.async(proxy)
asyncresult=async.divide(100,5)
# set a chain of callables to be invoked once the value is available
# but we set it 'too late' (when the result is already available)
time.sleep(4)  # result will appear in 3 seconds
asyncresult.then(asyncFunction) \
           .then(asyncFunction) \
           .then(asyncFunction)
# let's see what the result value is, should be 100/5+3=23
print("final value=",asyncresult.value)
assert asyncresult.value==23

print("\n* async call with call chain, where calls have extra arguments:")
async=Pyro4.async(proxy)
asyncresult=async.divide(100,5)
# set a chain of callables to be invoked once the value is available
# the callable will be invoked like so:  function(asyncvalue, kwarg=..., kwarg=...)
asyncresult.then(asyncFunction, increase=1) \
           .then(asyncFunction, increase=2) \
           .then(asyncFunction, increase=3)
print("sleeping 4 seconds")
time.sleep(4)   # the call chain will be invoked during this sleep period
print("back from sleep")
# you can still access the final asyncresult.value. It should be 100/5+1+2+3=26
print("final value=",asyncresult.value)
assert asyncresult.value==26

print("\n* async call with call chain, where calls are new pyro calls:")
async=Pyro4.async(proxy)
asyncresult=async.divide(100,5)
# set a chain of callables to be invoked once the value is available
# the callable will be invoked like so:  function(asyncvalue, kwarg=..., kwarg=...)
asyncresult.then(proxy.add, increase=1) \
           .then(proxy.add, increase=2) \
           .then(proxy.add, increase=3)
print("getting result value (will block until available)")
print("final value=",asyncresult.value)
assert asyncresult.value==26    # 100/5+1+2+3=26

print("\ndone.")
