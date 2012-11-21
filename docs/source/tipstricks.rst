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


.. _future-functions:

Asynchronous ('future') normal function calls
=============================================
Pyro provides an async proxy wrapper to call remote methods asynchronously, see :ref:`async-calls`.
For normal Python code, Python provides a similar mechanism in the form of the
:py:class:`Pyro4.core.Future` class (also available as ``Pyro4.Future``).
With a syntax that is slightly different from normal method calls,
it provides the same asynchronous function calls as the async proxy has.

You create a ``Future`` object for a callable that you want to execute in the background,
and receive its results somewhere in the future::

    def add(x,y):
        return x+y

    futurecall = Pyro4.Future(add)
    result = futurecall(4,5)
    # do some other stuff... then access the value
    summation = result.value

Actually calling the `Future` object returns control immediately and results in a :py:class:`Pyro4.core.FutureResult`
object. This is the exact same class as with the async proxy. The most important attributes are ``value``, ``ready``
and the ``wait`` method. See :ref:`async-calls` for more details.

You can also chain multiple calls, so that the whole call chain is executed sequentially in the background.
Rather than doing this on the ``FutureResult`` result object, you should do it directly on the ``Future`` object,
with the :py:meth:`Pyro4.core.Future.then` method. It has the same signature as the ``then`` method from
the ``FutureResult`` class::

    futurecall = Pyro4.Future(something)
    futurecall.then(somethingelse, 44)
    futurecall.then(lastthing, optionalargument="something")

See the :file:`futures` example for more details and example code.

