This example shows some code that triggers a Pyro conversation deadlock.

The client and server engage in a 'conversation' where they will deadlock
because a single proxy is used for both the initial server method call,
and client callback.
The client callback method calls the server again.
But it will fail, because the proxy it is using is still engaged in the
original method call to the server and is locked (waiting for a response).

A simple solution is to never reuse proxies in callbacks, and instead
create new ones and use those in the callback functions.

Another solution is to set COMMTIMEOUT such that after a certain time the
client will abort with a timeout error, effectively breaking the deadlock.
