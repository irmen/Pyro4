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
two remote messages for every method invocation on the proxy.

Note that the custom proxy class shown in the client uses some advanced features
of the Pyro API:
 - overrides internal method that handles method calls
 - creates and receives custom wire protocol messages
