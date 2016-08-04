from __future__ import print_function
import Pyro4
import bouncer


# you could set a comm timeout to avoid the deadlock situation...:
# Pyro4.config.COMMTIMEOUT = 2

with Pyro4.Daemon() as daemon:
    uri = daemon.register(bouncer.Bouncer("Server"))
    Pyro4.locateNS().register("example.deadlock", uri)

    print("This bounce example will deadlock!")
    print("Read the source or Readme.txt for more info why this is the case!")
    print("Bouncer started.")
    daemon.requestLoop()
