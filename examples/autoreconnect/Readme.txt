This is an example that shows the auto reconnect feature.

Start the server and the client.
You can stop the server while it's running.
The client will report that the connection is lost, and that
it is trying to rebind.
Start the server again. You'll see that the client continues.

There are 2 examples:
- reconnect using NS (clientNS/serverNS)
- reconnect using PYRO (client/server)


NOTES:

1- Your server has to be prepared for this feature. It must not rely
   on any transient internal state to function correctly, because
   that state is lost when your server is restarted. You could make
   the state persistent on disk and read it back in at restart.
2- By default Pyro starts its daemons on a random port. If you want
   to support autoreconnection, you will need to restart your daemon
   on the port it used before. Easiest is to pick a fixed port.
3- If using the name server or relying on PYRO-uri's: then your server
   MUST register the objects with their old objectId to the daemon.
   Otherwise the client will try to access an unknown object Id.
4- If the NS loses its registrations, you're out of luck.
   Clients that rely on name server based reconnects will fail.
5- The client is reponsible for detecting a network problem itself.
   It must also explicitly call the reconnect method on the object.
6- Why isn't this automagic? Because you need to have control about
   it when a network problem occurs. Furthermore, only you can decide
   if your system needs this feature, and if it can support it
   (see points above).
7- Read the source files for info on what is going on.
