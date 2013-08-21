.. _tipstricks:

*************
Tips & Tricks
*************

Best practices
==============

Avoid circular communication topologies.
----------------------------------------
When you can have a circular communication pattern in your system (A-->B-->C-->A) this can cause some problems:

* when reusing a proxy it causes a deadlock because the proxy is already being used for an active remote call. See the :file:`deadlock` example.
* with the multiplex servertype, the server itself may also block for all other remote calls because the handling of the first is not yet completed.

Avoid circularity, or use *oneway* method calls on at least one of the links in the chain.

Release your proxies if you can.
--------------------------------
A connected proxy that is unused takes up resources on the server. In the case of the threadpool server type,
it locks up a single thread. If you have too many connected proxies at the same time, the server may run out
of threads and stops responding. (The multiplex server doesn't have this particular issue).
It is a good thing to think about when you can release a proxy in your code.
Don't worry about reconnecting, that's done automatically once it is used again.
You can use explicit ``_pyroRelease`` calls or use the proxy from within a context manager.
It's not a good idea to release it after every single remote method call though, because then the cost
of reconnecting the socket will cause a serious drop in performance (unless every call is at least a few seconds after the previous one).

Avoid large binary blobs over the wire.
---------------------------------------
Pyro is not designed to efficiently transfer large amounts of binary data over the network.
Try to find another protocol that better suits this requirement.
Read :ref:`binarytransfer` for some more details about this.

Minimize object graphs that travel over the wire.
-------------------------------------------------
Pyro will serialize the whole object graph you're passing, even when only a tiny fraction
of it is used on the receiving end. Be aware of this: it may be necessary to define special lightweight objects
for your Pyro interfaces that hold the data you need, rather than passing a huge object structure.


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


Same major Python version required
==================================

When Pyro is configured to use pickle as its serialization format, it is required to have the same *major* Python versions
on your clients and your servers. Otherwise the different parties cannot decipher each others serialized data.
This means you cannot let Python 2.x talk to Python 3.x with Pyro. However
it should be fine to have Python 2.6.2 talk to Python 2.7.3 for instance.
Using one of the implementation independent protocols (serpent or json) will avoid this limitation.


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
:py:class:`Pyro4.futures.Future` class (also available as ``Pyro4.Future``).
With a syntax that is slightly different from normal method calls,
it provides the same asynchronous function calls as the async proxy has.
Note that Python itself has a similar thing in the standard library since version 3.2, see
http://docs.python.org/3/library/concurrent.futures.html#future-objects . However Pyro's Future
object is available on older Python versions too, and works slightly differently. It's
also a little bit easier to work with.

You create a ``Future`` object for a callable that you want to execute in the background,
and receive its results somewhere in the future::

    def add(x,y):
        return x+y

    futurecall = Pyro4.Future(add)
    result = futurecall(4,5)
    # do some other stuff... then access the value
    summation = result.value

Actually calling the `Future` object returns control immediately and results in a :py:class:`Pyro4.futures.FutureResult`
object. This is the exact same class as with the async proxy. The most important attributes are ``value``, ``ready``
and the ``wait`` method. See :ref:`async-calls` for more details.

You can also chain multiple calls, so that the whole call chain is executed sequentially in the background.
Rather than doing this on the ``FutureResult`` result object, you should do it directly on the ``Future`` object,
with the :py:meth:`Pyro4.futures.Future.then` method. It has the same signature as the ``then`` method from
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
(go to Network Settings, enable "Assign hostname to loopback IP").

If Pyro detects a problem with the dns setup it will log a WARNING in the logfile (if logging is enabled),
something like: ``weird DNS setup: your-computer-hostname resolves to localhost (127.x.x.x)``


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

.. note::
    In some situations the NAT simply is configured to pass through any port one-to-one to another
    host behind the NAT router/firewall. Pyro facilitates this by allowing you to set the natport
    to 0, in which case Pyro will replace it by the internal port number.


.. _binarytransfer:

Binary data transfer
====================
Pyro is not meant as a tool to transfer large amounts of binary data (images, sound files, video clips).
Its wire protocol is not optimized for these kinds of data. The occasional transmission of such data
is fine (:doc:`flame` even provides a convenience method for that, if you like:
:meth:`Pyro4.utils.flame.Flame.sendfile`) but usually it is better to use something else to do
the actual data transfer (file share+file copy, ftp, scp, rsync).

The following table is an indication of the relative speeds when dealing with large amounts
of binary data. It lists the results of the :file:`hugetransfer` example, using python 3.3,
over a 100 mbit lan connection:

========== ========== ============= ================
serializer str mb/sec bytes mb/sec  bytearray mb/sec
========== ========== ============= ================
pickle     30.9       32.8          31.8
marshal    30.0       28.8          32.4
serpent    12.5       9.1           9.1
json       22.5       not supported not supported
========== ========== ============= ================

The json serializer can't deal with actual binary data at all because it can't serialize these types.
The serpent serializer is particularly inefficient when dealing with binary data, because by design,
it has to encode and decode it as a base-64 string.

Marshal and pickle are relatively efficient. But here is a short overview of the ``pickle``
wire protocol overhead for the possible binary types:

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


MSG_WAITALL socket option
=========================
Pyro will use the ``MSG_WAITALL`` socket option to receive large messages, if it decides that
the feature is available and working correctly. On most systems that define the ``socket.MSG_WAITALL``
symbol, it does, except on Windows: even though the option is there, it doesn't work reliably.
If you want to check in your code what Pyro's behavior is, see the ``socketutil.USE_MSG_WAITALL`` attribute
(it's a boolean that will be set to False if Pyro decides it can't or should not use MSG_WAITALL).


IPV6 support
============
Pyro4 supports IPv6 since version 4.18. You can use IPv6 addresses in the same places where you would
normally have used IPv4 addresses. There's one exception: the address notation in a Pyro URI. For a numeric
IPv6 address in a Pyro URI, you have to enclose it in brackets. For example:

``PYRO:objectname@[::1]:3456``

points at a Pyro object located on the IPv6 "::1" address (localhost). When Pyro displays a numeric
IPv6 location from an URI it will also use the bracket notation. This bracket notation is only used
in Pyro URIs, everywhere else you just type the IPv6 address without brackets.

To tell Pyro to prefer using IPv6 you can use the ``PREFER_IP_VERSION`` config item. It is set to 4 by default,
for backward compatibility reasons.
This means that unless you change it to 6 (or 0), Pyro will be using IPv4 addressing.

There is a new method to see what IP addressing is used: :py:meth:`Pyro4.socketutil.getIpVersion`,
and a few other methods in :py:mod:`Pyro4.socketutil`  gained a new optional argument to tell it if
it needs to deal with an ipv6 address rather than ipv4, but these are rarely used in client code.
