from __future__ import print_function
import time
import Pyro4


with Pyro4.core.Proxy("PYRONAME:example.oneway") as serv:
    print("starting server using a oneway call")
    serv.oneway_start(6)
    print("doing some more oneway calls inbetween")
    serv.nothing()
    serv.nothing()
    serv.nothing()
    serv.nothing()

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
    print("\nCalling oneway work method, server will continue working while we are done (check the server console output).")
    serv.oneway_work()
