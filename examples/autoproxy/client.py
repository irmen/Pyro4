from __future__ import print_function
import sys
import Pyro4

if sys.version_info<(3,0):
    input=raw_input


uri=input("enter factory server object uri: ").strip()
factory=Pyro4.Proxy(uri)

# create several things.
print("Creating things.")
thing1 = factory.createSomething(1)
thing2 = factory.createSomething(2)
thing3 = factory.createSomething(3)

# interact with them on the server.
print("Speaking stuff.")
thing1.speak("I am the first")
thing2.speak("I am second")
thing3.speak("I am last then...")

