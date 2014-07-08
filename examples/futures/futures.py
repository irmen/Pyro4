from __future__ import print_function
import Pyro4


def myfunction(a, b, extra=None):
    print(">>> myfunction called with: a={0}, b={1}, extra={2}".format(a, b, extra))
    return a + b


print("\n* just a single future call:")
future = Pyro4.Future(myfunction)
result = future(5, 6)
# we can do stuff here in the meantime...
print("result value=", result.value)
assert result.value == 11

print("\n* several calls chained:")
future = Pyro4.Future(myfunction)
future.then(myfunction, 10)
future.then(myfunction, 20, extra="something")
# the callables will be invoked like so:  function(asyncvalue, normalarg, kwarg=..., kwarg=...)
# (the value from the previous call is passed as the first argument to the next call)
result = future(5, 6)
# we can do stuff here in the meantime...
print("result value=", result.value)
assert result.value == 41
