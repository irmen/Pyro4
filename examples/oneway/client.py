#!/usr/bin/env python

import time
import Pyro.core

serv = Pyro.core.Proxy("PYRONAME:test.oneway")
serv._pyroOneway.add("start")
serv._pyroOneway.add("nothing")
serv._pyroOneway.add("nonexisting")

print "starting server using a oneway call"
serv.start()
print "doing some more oneway calls inbetween"
serv.nothing()
serv.nothing()
serv.nothing()
try:
    serv.nonexisting()
    print "huh? this should fail because of an unexisting method"
except AttributeError:
    pass

print "doing some stuff..."
time.sleep(4)
print "now contacting the server to see if it's done."
print "we are faster, so you should see a few attempts,"
print "until the server is finished."
while True:
    print "server done?"
    if serv.ready():
        print "yes!"
        break
    else:
        print "no, trying again"
        time.sleep(1)

print "getting the result from the server:",serv.result()
