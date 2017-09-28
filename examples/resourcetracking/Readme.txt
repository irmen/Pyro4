This example shows how you can utilize the resource tracking feature to properly
close allocated resources when a client connection gets closed forcefully before
the client can properly free the resources itself.

The client allocates and frees some (fictional) resources.

The server registers them as tracked resources for the current client connection.
If you kill the client before it can cleanly free the resources, Pyro will
free them for you as soon as the connection to the server is closed.
