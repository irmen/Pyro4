from __future__ import print_function
import sys
import time

import Pyro4


if sys.version_info < (3, 0):
    input = raw_input


def asyncFunction(values):
    results = [value + 1 for value in values]
    print(">>> async batch function called, returning:", results)
    return results


uri = input("enter async server object uri: ").strip()
proxy = Pyro4.Proxy(uri)

print("\n* batch async call:")
batch = Pyro4.batch(proxy)
batch.divide(100, 5)
batch.divide(99, 9)
batch.divide(555, 2)
print("getting results...")
asyncresults = batch(async=True)  # returns immediately
print("result value available?", asyncresults.ready)  # prints False because the server is still 'busy'
print("client can do other stuff here.")
time.sleep(2)
print("such as sleeping ;-)")
time.sleep(2)
print("sleeping some more, batch takes a while")
time.sleep(2)
print("getting result values...(will block until available)")
results = asyncresults.value  # blocks until the result is available
print("resultvalues=", list(results))

print("\n* batch async call with chained function:")
batch = Pyro4.batch(proxy)
batch.divide(100, 5)
batch.divide(99, 9)
batch.divide(555, 2)
asyncresults = batch(async=True)  # returns immediately
asyncresults.then(asyncFunction) \
    .then(asyncFunction) \
    .then(asyncFunction)
print("getting result values...(will block until available)")
print("final value=", asyncresults.value)

print("\n* batch async call with exception:")
batch = Pyro4.batch(proxy)
batch.divide(1, 1)  # first call is ok
batch.divide(100, 0)  # second call will trigger a zero division error, 100//0
asyncresults = batch(async=True)  # returns immediately
print("getting result values...")
try:
    value = asyncresults.value
    print("Weird, this shouldn't succeed!?... resultvalues=", list(value))
except ZeroDivisionError:
    print("got exception (expected):", repr(sys.exc_info()[1]))

print("\n* batch async call with timeout:")
batch = Pyro4.batch(proxy)
batch.divide(100, 5)
batch.divide(99, 9)
batch.divide(555, 2)
asyncresults = batch(async=True)  # returns immediately
print("checking if ready within 2 seconds...")
ready = asyncresults.wait(2)  # wait for ready within 2 seconds but the server takes 3
print("status after wait=", ready)  # should print False
print("checking again if ready within 10 seconds...(should be ok now)")
ready = asyncresults.wait(timeout=10)  # wait 10 seconds now (but server will be done within ~8 more seconds)
print("status after wait=", ready)
print("available=", asyncresults.ready)
results = asyncresults.value
print("resultvalues=", list(results))

print("\ndone.")
