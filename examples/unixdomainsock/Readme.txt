This is a very simple example that uses a Unix domain socket instead of 
a normal tcp/ip socket for server communications.

The only difference is the parameter passed to the Daemon class.
The client code is unaware of any special socket because you just
feed it any Pyro URI. This time the URI will encode a Unix domain socket
however, instead of a hostname+port number.

