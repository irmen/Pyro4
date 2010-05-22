This example shows how you can let a server call back to the client.

The client creates some worker objects on the server. It provides them
with (a proxy of) a callback object that lives in the client.
When a worker is done with its task, it will invoke a method on the
callback object. That means that this time, the client gets a call
from the server that notifies it that a worker has completed its job.

(Note: the client uses oneway calls to start up the workers, this
ensures that they are running in the background)

For al this to work, the client needs to create a daemon as well:
it needs to be able to receive (callback) calls after all.
So it creates a deamon, a callback receiver, and starts it all up just
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
