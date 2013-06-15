Example code that shows a possible way to deal with client disconnects in the server.

It sets the COMMTIMEOUT config item on the server side.
This will make the connections timeout after the given time if no more data is received.
That connection will then be terminated.

The problem with this is, that a client that is still connected but simply takes too
long between remote method calls, will encounter a ConnectionClosedError.
But you can use Pyro's auto-reconnect feature to deal with this.

The client.py code creates a special Proxy class that you use instead of Pyro's
default, which will automatically do this for you on every method call.
Alternatively you can do it explicitly in your own code like the 'autoreconnect'
client example does.

A drawback of the code shown is that it is not very efficient; it now requires
two remote calls for every method invocation on the proxy.
Perhaps it can be improved to not use the 'ping' method
and simply retrying the actual method if that fails. The problem with that is
unfortunately we have no way of knowing if the first call was received and processed by
the server and the disconnect happened only after that (before receiving the response).
Calling the same method again after reconnecting might result in the method being
invoked twice in the server, and that's usually not what you want to happen.


