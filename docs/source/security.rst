.. _security:

Security (@todo)
****************

.. note::
  This still needs to be written

Warning about exposing Pyro over the internet.
But by default, Pyro only uses the local loopback network. You have to explicitly tell it to expose and use ports on remotely accessible interface.
Also there is a HMAC signature to prevent malicious requests. Need to set it yourself with a secure shared key, will give warning if left un-enabled.
It is hard to keep a shared secret key actually secret (people might read your source code).

There is no protocol encryption! (yet, possibly SSL in the future)
Dotted names are disallowed by default because they are a security vulnerability (for similar reasons as described here http://www.python.org/news/security/PSF-2005-001/ ).


Be aware that every Pyro object in a daemon can access any other Pyro object easily via the daemon's internal data structure.
There are many other ways to access arbitrary objects in Python but this one is so simple it might be helpful to point it out.
It should not be a problem in practice: you should never assume anyway that objects in the same Python process are separated from each other.
