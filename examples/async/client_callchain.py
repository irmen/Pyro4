from __future__ import print_function
import sys
import time

import Pyro4


if sys.version_info < (3, 0):
    input = raw_input


def asyncFunction(value, increase=1):
    print(">>> async function called with value={0} increase={1}".format(value, increase))
    return value + increase


def asyncWithMoreArgs(a, b, extra=None):
    print(">>> async func called with some arguments: a={0}, b={1}, extra={2}".format(a, b, extra))
    return a + b


uri = input("enter async server object uri: ").strip()
proxy = Pyro4.Proxy(uri)

print("\n* async call with error:")
proxy._pyroAsync()
def resulthandler(result):
    print("RESULT: ", result)
def errorhandler(error):
    print("ERRORHANDLER: ", error)
asyncresult = proxy.divide(100, 0).iferror(errorhandler).then(resulthandler)
time.sleep(4)
print("^^^^ above an error message should be printed out...")
print("\n* async call with error, but without errorhandler:")
asyncresult = proxy.divide(100, 0).then(resulthandler)
time.sleep(4)
print("^^^^ above, no error message should be printed out...")
try:
    _ = asyncresult.value
    print("SHOULD RAISE ERROR INSTEAD!!")
except ZeroDivisionError as x:
    print("expected error occurred when trying to obtain the result:", x)

print("\n* async call with call chain:")
asyncresult = proxy.divide(100, 5)
# set a chain of callables to be invoked once the value is available
asyncresult.then(asyncFunction) \
    .then(asyncFunction) \
    .then(asyncFunction)
print("sleeping 4 seconds")
time.sleep(4)  # the call chain will be invoked during this sleep period
print("back from sleep")
# you can still access the final asyncresult.value. It should be 100/5+3=23
print("final value=", asyncresult.value)
assert asyncresult.value == 23

print("\n* async call with call chain that is set 'too late':")
asyncresult = proxy.divide(100, 5)
# set a chain of callables to be invoked once the value is available
# but we set it 'too late' (when the result is already available)
time.sleep(4)  # result will appear in 3 seconds
asyncresult.then(asyncFunction) \
    .then(asyncFunction) \
    .then(asyncFunction)
# let's see what the result value is, should be 100/5+3=23
print("final value=", asyncresult.value)
assert asyncresult.value == 23

print("\n* async call with call chain, where calls have extra arguments:")
asyncresult = proxy.multiply(5, 6)
# set a chain of callables to be invoked once the value is available
# the callable will be invoked like so:  function(asyncvalue, normalarg, kwarg=..., kwarg=...)
# (the value from the previous call is passed as the first argument to the next call)
asyncresult.then(asyncWithMoreArgs, 1) \
    .then(asyncWithMoreArgs, 2, extra=42) \
    .then(asyncWithMoreArgs, 3, extra="last one")
print("sleeping 1 second")
time.sleep(1)  # the call chain will be invoked during this sleep period
print("back from sleep")
# you can still access the final asyncresult.value. It should be 5*6+1+2+3=36
print("final value=", asyncresult.value)
assert asyncresult.value == 36

print("\n* async call with call chain, where calls are new non-async pyro calls:")
normalproxy = Pyro4.Proxy(uri)
asyncresult = proxy.divide(100, 5)
# set a chain of callables to be invoked once the value is available
# the callable will be invoked like so:  function(asyncvalue, kwarg=..., kwarg=...)
asyncresult.then(normalproxy.add, increase=1) \
    .then(normalproxy.add, increase=2) \
    .then(normalproxy.add, increase=3)
print("getting result value (will block until available)")
print("final value=", asyncresult.value)
assert asyncresult.value == 26  # 100/5+1+2+3=26

print("\ndone.")
