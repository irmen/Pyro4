# this example forks() and thus won't work on Windows.

from __future__ import print_function
import os
import signal
import socket
import Pyro4

# it's okay to use Pickle because we trust our own processes, and it is efficient
Pyro4.config.SERIALIZER = "pickle"
Pyro4.config.SERIALIZERS_ACCEPTED |= {"pickle"}


# create our own socket pair (server-client sockets that are already connected)
sock1, sock2 = socket.socketpair()

pid = os.fork()

if pid == 0:
    # we are the child process, we host the daemon.

    class Echo(object):
        @Pyro4.expose
        def echo(self, message):
            print("server got message: ", message)
            return "thank you"

    # create a daemon with some Pyro objectrunning on our custom server socket
    daemon = Pyro4.Daemon(connected_socket=sock1)
    daemon.register(Echo, "echo")
    print("Process PID={:d}: Pyro daemon running on {:s}\n".format(os.getpid(), daemon.locationStr))
    daemon.requestLoop()

else:
    # we are the parent process, we create a Pyro client proxy
    print("Process PID={:d}: Pyro client.\n".format(os.getpid()))

    # create a client running on the client socket
    with Pyro4.Proxy("echo", connected_socket=sock2) as p:
        reply = p.echo("hello!")
        print("client got reply:", reply)
        reply = p.echo("hello again!")
        print("client got reply:", reply)
    with Pyro4.Proxy("echo", connected_socket=sock2) as p:
        reply = p.echo("hello2!")
        print("client got reply:", reply)
        reply = p.echo("hello2 again!")
        print("client got reply:", reply)

    os.kill(pid, signal.SIGTERM)
    os.waitpid(pid, 0)
    print("\nThe end.")
