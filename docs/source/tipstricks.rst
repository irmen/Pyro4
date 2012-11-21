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


DNS setup
=========
Pyro depends on a working DNS configuration, at least for your local hostname (i.e. 'pinging' your local hostname should work).
If your local hostname doesn't resolve to an IP address, you'll have to fix this.
This can usually be done by adding an entry to the hosts file. For OpenSUSE, you can also use Yast to fix it
(go to Network Settings, enable "Assing hostname to loopback IP").


.. _nat-router:

Pyro behind a NAT router/firewall
=================================
You can run Pyro behind a NAT router/firewall.
Assume the external hostname is 'pyro.server.com' and the external port is 5555.
Also assume the internal host is 'server1.lan' and the internal port is 9999.
You'll need to have a NAT rule that maps pyro.server.com:5555 to server1.lan:9999.
You'll need to start your Pyro daemon, where you specify the ``nathost`` and ``natport`` arguments,
so that Pyro knows it needs to 'publish' URIs containing that *external* location instead of just
using the internal addresses::

    # running on server1.lan
    d = Pyro4.Daemon(port=9999, nathost="pyro.server.com", natport=5555)
    uri = d.register(Something(), "thing")
    print uri     # "PYRO:thing@pyro.server.com:5555"

As you see, the URI now contains the external address.

:py:meth:`Pyro4.core.Daemon.uriFor` by default returns URIs with a NAT address in it (if ``nathost``
and ``natport`` were used). You can override this by setting ``nat=False``::

    print d.uriFor("thing")                 # "PYRO:thing@pyro.server.com:5555"
    print d.uriFor("thing", nat=False)      # "PYRO:thing@localhost:36124"
    uri2 = d.uriFor(uri.object, nat=False)  # get non-natted uri

The Name server can also be started behind a NAT: it has a couple of command line options that
allow you to specify a nathost and natport for it. See :ref:`nameserver-nameserver`.

.. note::
    The broadcast responder always returns the internal address, never the external NAT address.
    Also, the name server itself won't translate any URIs that are registered with it.
    So if you want it to publish URIs with 'external' locations in them, you have to tell
    the Daemon that registers these URIs to use the correct nathost and natport as well.


Binary data transfer
====================
Pyro is not meant as a tool to transfer large amounts of binary data (images, sound files, video clips).
Its wire protocol is not optimized for these kinds of data. The occasional transmission of such data
is fine (:doc:`flame` even provides a convenience method for that, if you like:
:meth:`Pyro4.utils.flame.Flame.sendfile`) but usually it is better to use something else to do
the actual data transfer (file share+file copy, ftp, scp, rsync).

That being said, here is a short overview of the ``pickle`` wire protocol overhead for the possible types
you can use when transferring binary data using Pyro:

``str``
    *Python 2.x:* efficient; directly encoded as a byte sequence, because that's what it is.
    *Python 3.x:* inefficient; encoded in UTF-8 on the wire, because it is a unicode string.

``bytes``
    *Python 2.x:* same as ``str`` (available in Python 2.6 and 2.7)
    *Python 3.x:* efficient; directly encoded as a byte sequence.

``bytearray``
    Inefficient; encoded as UTF-8 on the wire (pickle does this in both Python 2.x and 3.x)

``array("B")`` (array of unsigned ints of size 1)
    *Python 2.x:* very inefficient; every element is encoded as a separate token+value.
    *Python 3.x:* efficient; uses machine type encoding on the wire (a byte sequence).

Your best choice, if you want to transfer binary data using Pyro, seems to be to use the ``bytes`` type
(and possibly the ``array("B")`` type if you're using Python 3.x, or just ``str`` if you're stuck on 2.5).
Stay clear from the rest. It is strange that the ``bytearray`` type is encoded so inefficiently by pickle.
