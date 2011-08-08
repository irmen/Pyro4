from __future__ import print_function
import Pyro4
import bouncer

daemon = Pyro4.Daemon()
uri = daemon.register(bouncer.Bouncer("Server"))
Pyro4.locateNS().register("example.deadlock",uri)

print("This bounce example will deadlock!")
print("Read the source or Readme.txt for more info why this is the case!")
print("Bouncer started.")
daemon.requestLoop()
