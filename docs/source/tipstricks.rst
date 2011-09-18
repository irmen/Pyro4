.. _tipstrics:

*************
Tips & Tricks
*************

Logging
=======
If you configure it (see :ref:`config-items`) Pyro will write a bit of debug information, errors, and notifications to a log file.
It uses Python's standard :py:mod:`logging` module for this.
Once enabled, your own program code could use Pyro's logging setup as well.
But if you want to configure your own logging, make sure you do that before any Pyro imports. Then Pyro will skip its own autoconfig.

Multiple network interfaces
===========================
This is a difficult subject but here are a few short notes about it.
*At this time, Pyro doesn't support running on multiple network interfaces at the same time*.
You can bind a deamon on INADDR_ANY (0.0.0.0) though, including the name server.
But weird things happen with the URIs of objects published through these servers, because they
will point to 0.0.0.0 and your clients won't be able to connect to the actual objects.

The name server however contains a little trick. The broadcast responder can also be bound on 0.0.0.0
and it will in fact try to determine the correct ip address of the interface that a client needs to use
to contact the name server on. So while you cannot run Pyro daemons on 0.0.0.0 (to respond to requests
from all possible interfaces), sometimes it is possible to run only the name server on 0.0.0.0.
The success ratio of all this depends heavily on your network setup.


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


