from __future__ import print_function

import Pyro4
from Pyro4.threadutil import Thread
import bouncer

abort = False

def PyroLoop(daemon):
    daemon.requestLoop()

def main():
    global abort
    daemon = Pyro4.Daemon()
    server = Pyro4.Proxy("PYRONAME:example.deadlock")

    bounceObj = bouncer.Bouncer("Client")
    daemon.register(bounceObj) # callback objece

    # register callback obj on theserver
    server.register(bounceObj)
    # register server as 'callback' on the bounce object in this client
    # note: we're using the same proxy here as the main program!
    # This is the main cause of the deadlock, because this proxy will already
    # be engaged in a call when the callback object here wants to use it as well.
    # One solution could be to use a new proxy from inside the callback object, like this:
    #   server2 = server.__copy__()
    #   bounceObj.register(server2)
    bounceObj.register(server)

    # create a thread that handles callback requests
    thread = Thread(target=PyroLoop, args=(daemon,))
    thread.setDaemon(True)
    thread.start()

    print("This bounce example will deadlock!")
    print("Read the source or Readme.txt for more info why this is the case!")

    print("Calling server...")
    result = server.process(["hello"])
    print("Result=", result)   # <--- you will never see this, it will deadlock in the previous call

if __name__ == '__main__':
    main()
