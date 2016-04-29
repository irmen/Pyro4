This example shows a possible use of a custom 'event loop'.
That means that your own program takes care of the main event loop,
and that it needs to detect when 'events' happen on the appropriate
Pyro objects. This particular example uses select to wait for the
set of objects (sockets, really) and calls the correct event handler.
You can add your own application's sockets easily this way.
See the 'sever_threads.py' how this is done.

Since Pyro 4.44 it is possible to easily merge/combine the event loops
of different daemons. This way you don't have to write your own event
loop multiplexer if you're only dealing with Pyro daemons.
See the 'server_multiplexed.py' how this is done.
(this only works for the multiplex server type, not for threaded).
