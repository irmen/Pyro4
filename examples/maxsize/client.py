from __future__ import print_function
import sys

import Pyro4
import Pyro4.errors


huge_object = [42] * 10000
simple_object = {"message": "hello", "irrelevant": huge_object}

print("First start the built-in test echo server with something like:")
print("$ python -m Pyro4.test.echoserver")
print("Enter the server's uri that was printed:")
if sys.version_info < (3, 0):
    uri = raw_input()
else:
    uri = input()
uri = uri.strip()
echoserver = Pyro4.Proxy(uri)

Pyro4.config.MAX_MESSAGE_SIZE = 0
print("\nSending big data with no limit on message size...")
response = echoserver.echo(simple_object)
print("success.")

try:
    Pyro4.config.MAX_MESSAGE_SIZE = 2500
    print("\nSending big data with a limit on message size...")
    response = echoserver.echo(simple_object)
    print("Hmm, this should have raised an exception")
except Pyro4.errors.MessageTooLargeError:
    ex_t, ex_v, ex_tb = sys.exc_info()
    print("EXCEPTION (expected):", ex_t, ex_v)
