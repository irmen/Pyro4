from __future__ import print_function
import sys
import time
import Pyro4

if sys.version_info<(3,0):
    input=raw_input


def asyncCallback(value):
    print(">>> async callback received:",value)


uri=input("enter async server object uri: ").strip()
proxy=Pyro4.Proxy(uri)

print("* normal call: (notice the delay)")
print("result=", proxy.divide(100,5))

print("\n* async call:")
async=proxy._pyroAsync()
asyncresult=async.divide(100,5)   # returns immediately
print("result value available?",asyncresult.ready())   # returns False because the server is still 'busy'
print("client can do other stuff here.")
print("getting result value...(will block until available)")
print("resultvalue=",asyncresult.value)   # blocks until the result is available

print("\n* async call with callback:")
async=proxy._pyroAsync(callback=asyncCallback)   # provide a callback function to be called when the result is available
asyncresult=async.divide(100,5)
print("sleeping 5 seconds")
time.sleep(5)   # the callback will occur in this sleep period
print("back from sleep, resultvalue=",asyncresult.value)   # can access result value here as well

print("\n* async call with exception:")
async=proxy._pyroAsync()
asyncresult=async.divide(100,0)   # will trigger a zero division error, 100//0
print("getting result value...")
try:
    value=asyncresult.value
    print("Weird, this shouldn't succeed!?... resultvalue=",value)
except ZeroDivisionError:
    print("got exception (expected):",repr(sys.exc_info()[1]))

print("\n* async call with timeout:")
async=proxy._pyroAsync()
asyncresult=async.divide(100,5)
print("checking if ready within 2 seconds...")
try:
    ready=asyncresult.ready(timeout=2)   # wait for ready within 2 seconds but the server takes 3
    print("Weird, this shouldn't succeed!?... available=",ready)
except Pyro4.errors.AsyncResultTimeout:
    print("got exception (expected):",repr(sys.exc_info()[1]))
print("checking again if ready within 5 seconds...(should be ok now)")
ready=asyncresult.ready(timeout=5)   # wait 5 seconds now (but server will be done within 1 more second)
print("available=",ready)
print("resultvalue=",asyncresult.value)

print("\ndone.")
