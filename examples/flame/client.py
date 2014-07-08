from __future__ import print_function
import sys

import Pyro4.utils.flame


if sys.version_info < (3, 0):
    input = raw_input

Pyro4.config.SERIALIZER = "pickle"  # flame requires pickle serializer

print("Start a Pyro Flame server somewhere.")
location = input("what is the location of the flame server, hostname:portnumber? ")
print()

# connect!
flame = Pyro4.utils.flame.connect(location)

# basic stuff
socketmodule = flame.module("socket")
osmodule = flame.module("os")
print("remote host name=", socketmodule.gethostname())
print("remote server current directory=", osmodule.getcwd())
flame.execute("import math")
root = flame.evaluate("math.sqrt(500)")
print("calculated square root=", root)
try:
    print("remote exceptions also work...", flame.evaluate("1//0"))
except ZeroDivisionError:
    print("(caught ZeroDivisionError)")

# print something to the remote server output
flame.builtin("print")("Hello there, remote server stdout!")

# upload a module source and call a function, on the server, in this new module
modulesource = open("stuff.py").read()
flame.sendmodule("flameexample.stuff", modulesource)
result = flame.module("flameexample.stuff").doSomething("hello", 42)
print("\nresult from uploaded module:", result)

# remote console
with flame.console() as console:
    print("\nStarting a remote console. Enter some commands to execute remotely. End the console as usual.")
    console.interact()
    print("Console session ended.")
