This is an example that shows the DOTTEDNAMES support and implications.

You can start the server with or without DOTTEDNAMES enabled.
Try both. See what the client does with both settings.

The client also tries to perform a security exploit in the server, which
will fail if DOTTEDNAMES is not enabled (the default).

Lastly, direct attribute access. This feature is not yet available in Pyro
so it cannot be demonstrated at this time.
