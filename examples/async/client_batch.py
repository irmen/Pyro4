from __future__ import print_function
import sys
import time
import Pyro4

if sys.version_info<(3,0):
    input=raw_input


def asyncCallback(values):
    print(">>> async batch callback received:",list(values))


uri=input("enter async server object uri: ").strip()
proxy=Pyro4.Proxy(uri)

print("\n* batch async call:")
batch=proxy._pyroBatch()
batch.divide(100,5)
batch.divide(99,9)
batch.divide(555,2)
print("getting results...")
asyncresults = batch(async=True)  # returns immediately
print("result value available?",asyncresults.ready())   # returns False because the server is still 'busy'
print("client can do other stuff here.")
time.sleep(2)
print("such as sleeping ;-)")
time.sleep(2)
print("sleeping some more, batch takes a while")
time.sleep(2)
print("getting result values...(will block until available)")
results=asyncresults.value   # blocks until the result is available
print("resultvalues=",list(results))

print("\n* batch async call with callback:")
batch=proxy._pyroBatch()
batch.divide(100,5)
batch.divide(99,9)
batch.divide(555,2)
asyncresults = batch(async=True, callback=asyncCallback)  # returns immediately
print("sleeping 12 seconds...")
time.sleep(12)   # the callback will occur in this sleep period
print("back from sleep!")
# remember; you cannot access asyncresult.value when using a callback!
assert asyncresults.ready()==False

print("\n* batch async call with exception:")
batch=proxy._pyroBatch()
batch.divide(1,1)   # first call is ok
batch.divide(100,0)   # second call will trigger a zero division error, 100//0
asyncresults = batch(async=True)  # returns immediately
print("getting result values...")
try:
    value=asyncresults.value
    print("Weird, this shouldn't succeed!?... resultvalues=",list(value))
except ZeroDivisionError:
    print("got exception (expected):",repr(sys.exc_info()[1]))

print("\n* batch async call with timeout:")
batch=proxy._pyroBatch()
batch.divide(100,5)
batch.divide(99,9)
batch.divide(555,2)
asyncresults = batch(async=True)  # returns immediately
print("checking if ready within 2 seconds...")
try:
    ready=asyncresults.ready(timeout=2)   # wait for ready within 2 seconds but the server takes 3
    print("Weird, this shouldn't succeed!?... available=",ready)
except Pyro4.errors.AsyncResultTimeout:
    print("got exception (expected):",repr(sys.exc_info()[1]))
print("checking again if ready within 10 seconds...(should be ok now)")
ready=asyncresults.ready(timeout=10)   # wait 10 seconds now (but server will be done within ~8 more seconds)
print("available=",ready)
results=asyncresults.value
print("resultvalues=",list(results))

print("\ndone.")
