from __future__ import print_function
import time
import Pyro4

serv = Pyro4.core.Proxy("PYRONAME:example.oneway")
serv._pyroOneway.add("start")
serv._pyroOneway.add("nothing")
serv._pyroOneway.add("nonexisting")

print("starting server using a oneway call")
serv.start(6)
print("doing some more oneway calls inbetween")
serv.nothing()
serv.nothing()
serv.nothing()
print("calling a non existing method, but since it is flagged oneway, we won't find out")
serv.nonexisting()

time.sleep(2)
print("\nNow contacting the server to see if it's done.")
print("we are faster, so you should see a few attempts,")
print("until the server is finished.")
while True:
    print("server done?")
    if serv.ready():
        print("yes!")
        break
    else:
        print("no, trying again")
        time.sleep(1)

print("getting the result from the server: %s" % serv.result())
