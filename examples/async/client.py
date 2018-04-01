from __future__ import print_function
import sys
import Pyro4


if sys.version_info < (3, 0):
    input = raw_input

uri = input("enter async server object uri: ").strip()
proxy = Pyro4.Proxy(uri)

print("* normal call: (notice the delay)")
print("result=", proxy.divide(100, 5))

print("\n* async call:")
proxy._pyroAsync()
asyncresult = proxy.divide(100, 5)  # returns immediately
print("result value available?", asyncresult.ready)  # prints False because the server is still 'busy'
print("client can do other stuff here.")
print("getting result value...(will block until available)")
print("resultvalue=", asyncresult.value)  # blocks until the result is available

print("\n* async call, with normal call inbetween:")
normalproxy = Pyro4.Proxy(uri)
asyncresult = proxy.divide(100, 5)  # returns immediately
print("client does normal call: ", normalproxy.multiply(5, 20))
print("client does normal call: ", normalproxy.multiply(5, 30))
print("getting result value of async call...(will block until available)")
print("resultvalue=", asyncresult.value)  # blocks until the result is available

print("\n* async call with exception:")
asyncresult = proxy.divide(100, 0)  # will trigger a zero division error, 100//0
print("getting result value...")
try:
    value = asyncresult.value
    print("Weird, this shouldn't succeed!?... resultvalue=", value)
except ZeroDivisionError as x:
    print("got exception (expected):", repr(x))

print("\n* async call with timeout:")
asyncresult = proxy.divide(100, 5)
print("checking if ready within 2 seconds...")
ready = asyncresult.wait(2)  # wait for ready within 2 seconds but the server takes 3
print("status after waiting=", ready)  # should print False
print("checking again if ready within 5 seconds...(should be ok now)")
ready = asyncresult.wait(timeout=5)  # wait 5 seconds now (but server will be done within 1 more second)
print("status after waiting=", ready)
print("available=", asyncresult.ready)
print("resultvalue=", asyncresult.value)

print("\n* a few async calls at the same time:")
results = [
    proxy.divide(100, 7),
    proxy.divide(100, 6),
    proxy.divide(100, 5),
    proxy.divide(100, 4),
    proxy.divide(100, 3),
]
print("getting values...")
for result in results:
    print("result=", result.value)

print("\ndone.")
