These examples shows how you can let a server call back to the client.
There are 2 examples.

1) first example: server.py + client.py

The client creates some worker objects on the server. It provides them
with a callback object that lives in the client.
When a worker is done with its task, it will invoke a method on the
callback object. That means that this time, the client gets a call
from the server that notifies it that a worker has completed its job.

(Note: the client uses oneway calls to start up the workers, this
ensures that they are running in the background)

For all of this to work, the client needs to create a daemon as well:
it needs to be able to receive (callback) calls after all.
So it creates a daemon, a callback receiver, and starts it all up just
like a server would do.

The client counts the number of 'work completed' callbacks it receives.
To remain in the daemon loop, the client provides a special loop condition
that is true while the counter is less than the number of workers.


Notice that the client sets PYRO_COMMTIMEOUT.
That is needed because otherwise it will block in the default requestloop,
and it will never evaluate the loopcondition. By setting a timeout we
force it to periodically break from the blocking wait and check the
loop condition.  We could also have used the 'select' servertype instead
of setting a PYRO_COMMTIMEOUT, because that one already breaks periodically.
(PYRO_POLLTIMEOUT).


2) second example: server2.py + client2.py

This example shows how to use the @Pyro4.callback decorator to flag a method
to be a callback method. This makes Pyro log any exceptions that occur in
this method also on the side where the method is running. Otherwise it would
just silently pass the exception back to the side that was calling the
callback method, and there is no way to see it occur on the callback side itself.

It only logs a warning with the error and the traceback though. It doesn't
actually print it to the screen, or raise the exception again. So you have to
enable logging to see it appear.


Also note that this example makes use of Pyro's AutoProxy feature. Sending
pyro objects 'over the wire' will automatically convert them into proxies so
that the other side will talk to the actual object, instead of a local copy.
So the client just sends a callback object to the server, and the server can
just return a worker object, as if it was a normal method call.
