.. _security:

Security (@todo)
****************

.. note::
  This still needs to be written

Warning about exposing Pyro over the internet.
But by default, Pyro only uses the local loopback network. You have to explicitly tell it to expose and use ports on remotely accessible interface.
Also there is a HMAC signature to prevent malicious requests. Need to set it yourself with a secure shared key, will give warning if left un-enabled.
There is no protocol encryption! (yet, possibly SSL in the future)
Dotted names are disallowed by default because they are a security vulnerability (for similar reasons as described here http://www.python.org/news/security/PSF-2005-001/ ).

