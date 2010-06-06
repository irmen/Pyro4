This example shows a possible use of a custom 'event loop'.
That means that your own program takes care of the main event loop,
and that it needs to detect when 'events' happen on the appropriate
Pyro objects. This particular example uses select to wait for the
set of objects (sockets, really) and calls the correct event handler.
You can add your own application's sockets easily this way.
