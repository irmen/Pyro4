These SSL/TLS certificates are self-signed and have no CA trust chain.
They contain some info to see that they're for Pyro4 (O=Razorvine.net, OU=Pyro4, CN=localhost)
They're meant to be used for testing purposes. There is no key password.

It's easy to make your own certs by the way, it's mentioned in the docs of the ssl module:
https://docs.python.org/3/library/ssl.html#self-signed-certificates

$ openssl req -new -x509 -days 365 -nodes -out cert.pem -keyout key.pem


It's also possible to make your own CA certs and sign your client and server certs
with them, but that is a lot more elaborate.
