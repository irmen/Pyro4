Other stuff: these parts still need to be written
*************************************************

Pyro command line operation.
Name server (short overview, detailed info in its own chapter)
other script tools (nsc, configuration, test echo server).

Pyro servers.
How to write Pyro servers.
How to deal with the various server features.
Object concurrency model (when used with threaded server).
Network adapter bindings. Localhost (see security)
Daemon Pyro interface (see :class:`Pyro4.core.DaemonObject`).
Autoproxying.

Pyro clients.
How to write clients.
How to use the various client features.

Name server. Is a Pyro object itself.
Detailed info on how to start/configure it.
How to locate it.
The PYRO and PYRONAME protocol types.
Name server Pyro interface.

Security.
Warning about exposing Pyro over the internet.
But by default, Pyro only uses the local loopback network. You have to explicitly tell it to expose and use ports on remotely accessible interface.
Also there is a HMAC signature to prevent malicious requests. Need to set it yourself with a secure shared key, will give warning if left un-enabled.
There is no protocol encryption! (yet, possibly SSL in the future)
Dotted names are disallowed by default because they are a security vulnerability (for similar reasons as described here http://www.python.org/news/security/PSF-2005-001/ ).

Error handling.
Remote errors.
Remote tracebacks.
Troubleshooting?
