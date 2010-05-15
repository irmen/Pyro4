Shows the use of 'oneway' method calls.
If you flag a method call 'oneway', Pyro will not wait for a response
from the remote object. This means that your client program can continue to
work, while the remote object is still busy processing the method call.
(Normal remote method calls are synchronous and will always block until the
remote object is done with the method call).

This example also shows the use of the ONEWAY_THREADED setting in the
server. This setting is on by default. It means that oneway method calls
are executed in their own separate thread, so the server remains responsive
for additional calls from the same client even when the oneway call is still
running. If you set this to False, the server will process all calls from
the same proxy sequentially (and additional calls will have to wait).
Note that a different proxy will still be able to execute calls regardless
of the setting of ONEWAY_THREADED.
