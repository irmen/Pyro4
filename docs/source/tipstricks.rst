.. _tipstrics:

Tips & Tricks (@todo)
*********************

.. note::
  This still needs to be written

Various miscellaneous tips and tricks:

Logging.

If you need to resolve lots of objects, consider using the name server directly instead of :meth:`Pyro4.resolve` /:meth:`Pyro4.naming.resolve` or PYRONAME uris

Remember that URIs in proxies are unchanged. If you use many 'meta' uris (with PYRONAME) Pyro has to do a lookup everytime it needs to connect. Consider using PYRO uris or :meth:`Pyro4.core.Proxy._pyroBind()` if you want to avoid all the lookups.

Info on multi-interface computers and binding daemons on INADDR_ANY. (and the current inability of publishing objects on multiple interfaces)

If you make more connections to a daemon than its current thread pool, your client will hang until some connections have been freed, and worker threads have become available again.


Wire protocol version
=====================

Here is a little tip to find out what wire protocol version a given Pyro server is using.
This could be useful if you are getting ``ProtocolError: invalid data or unsupported protocol version``
or something like that. It also works with Pyro 3.x.

**Server**

This is a way to figure out the protocol version number a given Pyro server is using:
by reading the first 6 bytes from the server socket connection.
The Pyro daemon will respond with a 4-byte string "``PYRO``" followed by a 2-byte number
that is the protocol version used::

    $ nc pyroservername pyroserverport | od -N 6 -t x1c
    0000000  50  59  52  4f  00  05
              P   Y   R   O  \0 005

This one is talking protocol version ``00 05`` (5).
This low number means it is a Pyro 3.x server. When you try it on a Pyro 4 server::

    $ nc pyroservername pyroserverport | od -N 6 -t x1c
    0000000  50  59  52  4f  00  2c
              P   Y   R   O  \0   ,

This one is talking protocol version ``00 2c`` (44).
For Pyro4 the protocol version started at 40 for the first release
and is now at 44 for the current release at the time of writing.


**Client**

To find out the protocol version that your client code is using, you can use this::

    $ python -c "import Pyro4.constants as c; print(c.PROTOCOL_VERSION)"

or for Pyro3::

    $ python -c "import Pyro.protocol as p; print(p.PYROAdapter.version)"


