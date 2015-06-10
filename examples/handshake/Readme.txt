This example shows how you can customize the connection handshake mechanism.

The proxy is overridden to send custom handshake data to the daemon, in this case,
a "secret" string to gain access.

The daemon is overridden to check the handshake string and only allow a client
connection if it sends the correct "secret" string.


(This is not the same as the hmac key you can set. That is a signature of every
message to make sure it came unchanged from the client and wasn't altered mid-flight
by some middle man. The initial handshake check done here in this example,
is just a single initial check to allow a client to connect, or refuse it altogether.)
