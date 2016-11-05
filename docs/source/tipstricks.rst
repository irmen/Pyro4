.. index:: Tips & trics

.. _tipstricks:

*************
Tips & Tricks
*************

.. index:: Best practices

Best practices
==============

.. index:: circular topology

Avoid circular communication topologies.
----------------------------------------

When you can have a circular communication pattern in your system (A-->B-->C-->A) this can cause some problems:

* when reusing a proxy it causes a deadlock because the proxy is already being used for an active remote call. See the :file:`deadlock` example.
* with the multiplex servertype, the server itself may also block for all other remote calls because the handling of the first is not yet completed.

Avoid circularity, or use *oneway* method calls on at least one of the links in the chain.
Another possible way out of a lock situation is to set ``COMMTIMEOUT`` so that after a certain period in a locking
situation the caller aborts with a TimeoutError, effectively breaking the deadlock.

.. index:: releasing a proxy
.. _tipstricks_release_proxy:

'After X simultaneous proxy connections, Pyro seems to freeze!' Fix: Release your proxies when you can.
-------------------------------------------------------------------------------------------------------
A connected proxy that is unused takes up resources on the server. In the case of the threadpool server type,
it locks up a single thread. If you have too many connected proxies at the same time, the server may run out
of threads and won't be able to accept new connections.

You can use the ``THREADPOOL_SIZE`` config item to increase the maximum number of threads that Pyro will use.
Or use the multiplex server instead, which doesn't have this limitation.
Another option is to set ``COMMTIMEOUT`` to a certain value *on your server*, which will free up unused connections after the given time.
But your client code may now crash with a TimeoutError or ConnectionClosedError when it tries to use a proxy that worked earlier.
You can use Pyro's autoreconnect feature to work around this but it makes the code more complex.

It is however advised to close (release) proxies that your program no longer needs, to free resources
both in the client and in the server. Don't worry about reconnecting, Pyro does that automatically
for you once the proxy is used again.
You can use explicit ``_pyroRelease`` calls or use the proxy from within a context manager.
It's not a good idea to release it after every single remote method call though, because then the cost
of reconnecting the socket can be bad for performance.


.. index:: binary blob
    seealso: binary blob; binary data transfer

Avoid large binary blobs over the wire.
---------------------------------------
Pyro is not designed to efficiently transfer large amounts of binary data over the network.
Try to find another protocol that better suits this requirement.
Read :ref:`binarytransfer` for some more details about this.

Note that Pyro has a 2 gigabyte message size limitation at this time.


.. index:: object graphs

Minimize object graphs that travel over the wire.
-------------------------------------------------
Pyro will serialize the whole object graph you're passing, even when only a tiny fraction
of it is used on the receiving end. Be aware of this: it may be necessary to define special lightweight objects
for your Pyro interfaces that hold the data you need, rather than passing a huge object structure.


Consider using basic data types instead of custom classes.
----------------------------------------------------------
Because Pyro serializes the objects you're passing, it needs to know how to serialize custom types.
While you can teach Pyro about these (see :ref:`customizing-serialization`) it may sometimes be easier to just use a builtin datatype instead.
For instance if you have a custom class whose state essentially is a set of numbers, consider then
that it may be easier to just transfer a ``set`` or a ``list`` of those numbers rather than an instance of your
custom class.  It depends on your class and data ofcourse, and whether the receiving code expects
just the list of numbers or really needs an instance of your custom class.



.. index:: Logging

.. _logging:

Logging
=======
If you configure it (see :ref:`config-items`) Pyro will write a bit of debug information, errors, and notifications to a log file.
It uses Python's standard :py:mod:`logging` module for this (See https://docs.python.org/2/library/logging.html ).
Once enabled, your own program code could use Pyro's logging setup as well.
But if you want to configure your own logging, make sure you do that before any Pyro imports. Then Pyro will skip its own autoconfig.

A little example to enable logging by setting the required environment variables from the shell::

    $ export PYRO_LOGFILE=pyro.log
    $ export PYRO_LOGLEVEL=DEBUG
    $ python my_pyro_program.py

Another way is by modifiying ``os.environ`` from within your code itself, *before* any import of Pyro4 is done::

    import os
    os.environ["PYRO_LOGFILE"] = "pyro.log"
    os.environ["PYRO_LOGLEVEL"] = "DEBUG"

    import Pyro4
    # do stuff...

Finally, it is possible to initialize the logging by means of the standard Python ``logging`` module only, but
then you still have to tell Pyro4 what log level it should use (or it won't log anything)::

    import logging
    logging.basicConfig()  # or your own sophisticated setup
    logging.getLogger("Pyro4").setLevel(logging.DEBUG)
    logging.getLogger("Pyro4.core").setLevel(logging.DEBUG)
    # ... set level of other logger names as desired ...

    import Pyro4
    # do stuff...

The various logger names are similar to the module that uses the logger,
so for instance logging done by code in ``Pyro4.core`` will use a logger category name of ``Pyro4.core``.
Look at the top of the source code of the various modules from Pyro to see what the exact names are.


.. index:: multiple NICs, network interfaces

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


.. index:: same Python version

Same major Python version required when using pickle, dill or marshal
=====================================================================

When Pyro is configured to use pickle, dill or marshal as its serialization format, it is required to have the same *major* Python versions
on your clients and your servers. Otherwise the different parties cannot decipher each others serialized data.
This means you cannot let Python 2.x talk to Python 3.x with Pyro when using pickle, dill or marshal as serialization protocols. However
it should be fine to have Python 3.3 talk to Python 3.4 for instance.
It may still be required to specify the pickle or dill protocol version though, because that needs to be the same on both ends as well.
For instance, Python 3.4 introduced version 4 of the pickle protocol and as such won't be able to talk to Python 3.3 which is stuck
on version 3 pickle protocol. You'll have to tell the Python 3.4 side to step down to protocol 3. There is a config item for that. The same will apply for dill protocol versions.

The implementation independent serialization protocols serpent and json don't have these limitations.



.. index:: wire protocol version

.. _wireprotocol:

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

    $ nc <pyroservername> <pyroserverport> | od -N 6 -t x1c
    0000000  50  59  52  4f  00  05
              P   Y   R   O  \0 005

This one is talking protocol version ``00 05`` (5).
This low number means it is a Pyro 3.x server. When you try it on a Pyro 4 server::

    $ nc <pyroservername> <pyroserverport> | od -N 6 -t x1c
    0000000  50  59  52  4f  00  2c
              P   Y   R   O  \0   ,

This one is talking protocol version ``00 2c`` (44).
For Pyro4 the protocol version started at 40 for the first release
and is now at 46 for the current release at the time of writing.


**Client**

To find out the protocol version that your client code is using, you can use this::

    $ python -c "import Pyro4.constants as c; print(c.PROTOCOL_VERSION)"



.. index:: async, futures

.. _future-functions:

Asynchronous ('future') normal function calls
=============================================
Pyro provides an async proxy to call remote methods asynchronously, see :ref:`async-calls`.
For normal Python code, Python provides a similar mechanism in the form of the
:py:class:`Pyro4.futures.Future` class (also available as ``Pyro4.Future``).
With a syntax that is slightly different from normal method calls,
it provides the same asynchronous function calls as the async proxy has.
Note that Python itself has a similar thing in the standard library since version 3.2, see
http://docs.python.org/3/library/concurrent.futures.html#future-objects . However Pyro's Future
object is available on older Python versions too. It works slightly differently and perhaps
a little bit easier as well.

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
You can do this directly on the ``Future`` object,
with the :py:meth:`Pyro4.futures.Future.then` method. It has the same signature as the ``then`` method from
the ``FutureResult`` class::

    futurecall = Pyro4.Future(something) \
        .then(somethingelse, 44) \
        .then(lastthing, optionalargument="something")

There's also a :py:meth:`Pyro4.futures.Future.iferror` method that allows you to register a callback to be invoked
when an exception occurs. This method also exists on the ``FutureResult`` class.
See the :file:`futures` example for more details and example code.

You can delay the execution of the future for a number of seconds via the :py:meth:`Pyro4.futures.Future.delay` method,
and you can cancel it altogether via the :py:meth:`Pyro4.futures.Future.cancel` method (which only works if the future
hasn't been evaluated yet).


.. index:: DNS

DNS setup
=========
Pyro depends on a working DNS configuration, at least for your local hostname (i.e. 'pinging' your local hostname should work).
If your local hostname doesn't resolve to an IP address, you'll have to fix this.
This can usually be done by adding an entry to the hosts file. For OpenSUSE, you can also use Yast to fix it
(go to Network Settings, enable "Assign hostname to loopback IP").

If Pyro detects a problem with the dns setup it will log a WARNING in the logfile (if logging is enabled),
something like: ``weird DNS setup: your-computer-hostname resolves to localhost (127.x.x.x)``


.. index:: NAT, router, firewall

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
    uri = d.register(Something, "thing")
    print(uri)     # "PYRO:thing@pyro.server.com:5555"

As you see, the URI now contains the external address.

:py:meth:`Pyro4.core.Daemon.uriFor` by default returns URIs with a NAT address in it (if ``nathost``
and ``natport`` were used). You can override this by setting ``nat=False``::

    # d = Pyro4.Daemon(...)
    print(d.uriFor("thing"))                # "PYRO:thing@pyro.server.com:5555"
    print(d.uriFor("thing", nat=False))     # "PYRO:thing@localhost:36124"
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



.. index:: failed to locate the nameserver, connection refused

Failed to locate the nameserver / Connection refused, what now?
===============================================================

Usually when you get an error like "failed to locate the name server" or "connection refused" it is because
there is a configuration problem in your network setup, such as a firewall blocking certain network connections.
Sometimes it can be because you configured Pyro wrong. A checklist to follow to diagnose your issue can be as follows:

- can you ping the server from your client machine?
- can you telnet to the given host+port from your client machine?
- is the server's ip address as shown one of an externally reachable network interface?
- do you have your server behind a NAT router? See :ref:`nat-router`.
- do you have a firewall or packetfilter running that prevents the connection?
- do you have the same Pyro versions on both server and client?
- what does the pyro logfiles tell you (enable it via the config items on both the server and the client, including the name server. See :ref:`logging`.
- (if not using the default:) do you have a compatible serializer configuration?
- (if not using the default:) do you have a symmetric hmac key configuration?
- can you obtain a few bytes from the wire using netcat, see :ref:`wireprotocol`.


.. index:: binary data transfer, file transfer

.. _binarytransfer:

Binary data transfer / file transfer
====================================
Pyro is not meant to transfer large amounts of binary data (images, sound files, video clips):
the protocol is not designed nor optimized for these kinds of data. The occasional transmission of such data
is fine (:doc:`flame` even provides a convenience method for that, if you like:
:meth:`Pyro4.utils.flame.Flame.sendfile`) but if you're dealing with a lot of them or with big files,
it is usually better to use something else to do the actual data transfer (file share+file copy, ftp, http, scp, rsync).

Also, Pyro has a 2 gigabyte message size limitation at this time (if your Python implementation and
system memory even allow the process to reach this size).  You can avoid this problem if you use
the remote iterator feature (return chunks via an iterator or generator function and consume them
on demand in your client).

.. note:: Serpent and binary data:
    If you do transfer binary data using the serpent serializer, you have to be aware of the following.
    The wire protocol is text based so serpent has to encode any binary data. It uses base-64 to do that.
    This means on the receiving side, instead of the raw bytes, you get a little dictionary
    like this instead: ``{'data': 'aXJtZW4gZGUgam9uZw==', 'encoding': 'base64'}``
    Your client code needs to be aware of this and to get the original binary data back, it has to base-64
    decode the data element by itself.  This is perhaps done the easiest by using the
    ``serpent.tobytes`` helper function from the ``serpent`` library, which will convert
    the result to actual bytes if needed (and leave it untouched if it is already in bytes form)


The following table is an indication of the relative speeds when dealing with large amounts
of binary data. It lists the results of the :file:`hugetransfer` example, using python 3.5,
over a 1000 Mbps LAN connection:

========== ========== ============= ================ ====================
serializer str mb/sec bytes mb/sec  bytearray mb/sec bytearray w/iterator
========== ========== ============= ================ ====================
pickle     77.8       79.6          69.9             35.0
marshal    71.0       73.0          73.0             37.8
serpent    25.0       14.1          13.5             13.5
json       31.5       not supported not supported    not supported
========== ========== ============= ================ ====================

The json serializer only works with strings, it can't serialize binary data at all.
The serpent serializer can, but read the note above about why it's quite inefficent there.
Marshal and pickle are relatively efficient, speed-wise. But beware, when using ``pickle``,
there's quite a difference in dealing with various types:

**pickle datatype differences**

``str``
    *Python 2.x:* efficient; directly encoded as a byte sequence, because that's what it is.
    *Python 3.x:* inefficient; encoded in UTF-8 on the wire, because it is a unicode string.

``bytes``
    *Python 2.x:* same as ``str`` (Python 2.7)
    *Python 3.x:* efficient; directly encoded as a byte sequence.

``bytearray``
    Inefficient; encoded as UTF-8 on the wire (pickle does this in both Python 2.x and 3.x)

``array("B")`` (array of unsigned ints of size 1)
    *Python 2.x:* very inefficient; every element is encoded as a separate token+value.
    *Python 3.x:* efficient; uses machine type encoding on the wire (a byte sequence).

``numpy arrays``
    usually cannot be transferred directly, see :ref:`numpy`.


**integrating raw socket transfer in a Pyro server**

Have a look at the ``blobserver`` example to see an alternative for large binary transfers
where it is still mostly Pyro that does the job. But the actual data transfer is done over a
temporary raw socket connection. The transfer speed approaches the limits of my network adapter
in this case.


.. index:: MSG_WAITALL

MSG_WAITALL socket option
=========================
Pyro will use the ``MSG_WAITALL`` socket option to receive large messages, if it decides that
the feature is available and working correctly. This avoids having to use a slower function that
needs a loop to get all data. On most systems that define the ``socket.MSG_WAITALL``
symbol, it works fine, except on Windows: even though the option is there, it doesn't work reliably.
Pyro thus won't use it by default on Windows, and will use it by default on other systems.
You should set the ``USE_MSG_WAITALL`` config item to False yourself, if you find that your system has
an unreliable implementation of this socket option. Please let me know what system (os/python version)
it is so we could teach Pyro to select the correct option automatically in a new version.


.. index:: IPv6

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


.. index:: Numpy, numpy.ndarray
.. _numpy:

Pyro and Numpy
==============
More than once questions have been asked about Pyro and Numpy. More specifically, why certain errors occur when
people try to use numpy arrays with Pyro. Errors such as::

    TypeError: array([1, 2, 3]) is not JSON serializable
      or
    SerializeError: don't know how to serialize class <type 'numpy.ndarray'>

These errors are caused by Numpy datatypes not being serializable by serpent or json serializers.
So if you want to use them with Pyro, and pass them over the wire, you'll have to chose one of the following options:

#.  Don't use Numpy datatypes. Convert them to standard Python datatypes before using them in Pyro. So instead of just
    ``na = numpy.array(...); return na;``, use this instead:  ``return na.tolist()``.
    Or perhaps even ``return array.array('i', na)`` (serpent understands ``array.array``, but json doesn't)
    Note that the elements of a numpy array usually are of a special numpy datatype as well (such as ``numpy.int32``).
    If you don't convert these individually as well, you will still get serialization errors. That is why something like
    ``list(na)`` doesn't work: it seems to return a regular python list but the elements are still numpy datatypes.
    You have to use the full conversions as mentioned earlier.
#.  Don't return arrays at all. Redesign your API so that you might perhaps only return a single element from it.
#.  Tell Pyro to use :py:mod:`pickle` or :py:mod:`dill` as serializer. Pickle and Dill can deal with numpy datatypes. However they have security implications.
    See :doc:`security`. If you choose to use pickle or dill anyway, also be aware that you must tell your name server
    about it as well, see :ref:`nameserver-pickle`.


.. index::
    double: HTTP gateway server; command line
.. _http-gateway:

Pyro via HTTP and JSON
======================

.. sidebar:: advanced topic

    This is an advanced/low-level Pyro topic.

Pyro provides a HTTP gateway server that translates HTTP requests into Pyro calls. It responds with JSON messages.
This allows clients (including web browsers) to use a simple http interface to call Pyro objects.
Pyro's JSON serialization format is used so the gateway simply passes the JSON response messages back to the caller.
It also provides a simple web page that shows how stuff works.

*Starting the gateway:*

You can launch the HTTP gateway server via the command line tool.
This will create a web server using Python's :py:mod:`wsgiref` server module.
Because the gateway is written as a wsgi app, you can also stick it into a wsgi server of your own choice.
Import ``pyro_app`` from ``Pyro4.utils.httpgateway`` to do that (that's the app you need to use).


synopsys: :command:`python -m Pyro4.utils.httpgateway [options]` (or simply: :command:`pyro4-httpgateway [options]`)

A short explanation of the available options can be printed with the help option:

.. program:: Pyro4.utils.httpgateway

.. option:: -h, --help

   Print a short help message and exit.

Most other options should be self explanatory; you can set the listening host and portname etc.
An important option is the exposed names regex option: this controls what objects are
accessible from the http gateway interface. It defaults to something that won't just expose every
internal object in your system. If you want to toy a bit with the examples provided in the gateway's
web page, you'll have to change the option to something like: ``r'Pyro\.|test\.'`` so that those objects
are exposed. This regex is the same as used when listing objects from the name server, so you can use the
``nsc`` tool to check it (with the listmatching command).


*Using the gateway:*

You request the url ``http://localhost:8080/pyro/<<objectname>>/<<method>>`` to invoke a method on the
object with the given name (yes, every call goes through a naming server lookup).
Parameters are passed via a regular query string parameter list (in case of a GET request) or via form post parameters
(in case of a POST request). The response is a JSON document.
In case of an exception, a JSON encoded exception object is returned.
You can easily call this from your web page scripts using ``XMLHttpRequest`` or something like JQuery's ``$.ajax()``.
Have a look at the page source of the gateway's web page to see how this could be done.
Note that you have to comply with the browser's same-origin policy: if you want to allow your own scripts
to access the gateway, you'll have to make sure they are loaded from the same website.

The http gateway server is *stateless* at the moment. This means every call you do will end be processed by
a new Pyro proxy in the gateway server. This is not impacting your client code though, because every call that it
does is also just a stateless http call. It only impacts performance: doing large amounts of calls through
the http gateway will perform much slower as the same calls processed by a native Pyro proxy (which you can instruct
to operate in batch mode as well). However because Pyro is quite efficient, a call through
the gateway is still processed in just a few milliseconds, naming lookup and json serialization all included.

Special http request headers:

- ``X-Pyro-Options``: add this header to the request to set certain pyro options for the call. Possible values (comma-separated):

  - ``oneway``: force the Pyro call to be a oneway call and return immediately.
    The gateway server still returns a 200 OK http response as usual, but the response data is empty.
    This option is to override the semantics for non-oneway method calls if you so desire.

- ``X-Pyro-Gateway-Key``: add this header to the request to set the http gateway key. You can also set it on the request
  with a ``$key=....`` querystring parameter.


Special Http response headers:

-  ``X-Pyro-Correlation-Id``: contains the correlation id Guid that was used for this request/response.


Http response status codes:

- 200 OK: all went well, response is the Pyro response message in JSON serialized format
- 403 Forbidden: you're trying to access an object that is not exposed by configuration
- 404 Not Found: you're requesting a non existing object
- 500 Internal server error: something went wrong during request processing, response is serialized exception object (if available)


.. index:: current_context, correlation_id
.. _current_context:

Client information on the current_context, correlation id
=========================================================

.. sidebar:: advanced topic

    This is a very advanced/low-level Pyro topic.

Pyro provides a *thread-local* object with some information about the current Pyro method call,
such as the client that's performing the call. It is available as :py:data:`Pyro4.current_context`
(shortcut to :py:data:`Pyro4.core.current_context`).
When accessed in a Pyro server it contains various attributes:

.. py:attribute:: Pyro4.current_context.client

    (:py:class:`Pyro4.socketutil.SocketConnection`)
    this is the socket connection with the client that's doing the request.
    You can check the source to see what this is all about, but perhaps the single most useful
    attribute exposed here is ``sock``, which is the socket connection.
    So the client's IP address can for instance be obtained via :code:`Pyro4.current_context.client.sock.getpeername()[0]` .
    However, since for oneway calls the socket connection will likely be closed already, this is not 100% reliable.
    Therefore Pyro stores the result of the ``getpeername`` call in a separate attribute on the context:
    ``client_sock_addr`` (see below)

.. py:attribute:: Pyro4.current_context.client_sock_addr

    (*tuple*) the socket address of the client doing the call. It is a tuple of the client host address and the port.

.. py:attribute:: Pyro4.current_context.seq

    (*int*) request sequence number

.. py:attribute:: Pyro4.current_context.msg_flags

    (*int*) message flags, see :py:class:`Pyro4.message.Message`

.. py:attribute:: Pyro4.current_context.serializer_id

    (*int*) numerical id of the serializer used for this communication, see :py:class:`Pyro4.message.Message` .

.. py:attribute:: Pyro4.current_context.annotations

    (*dict*) message annotations, key is a 4-letter string and the value is a byte sequence.
    Pyro uses this for the few internal annotations such as ``HMAC`` and ``CORR``, which are reserved.
    But you can send your own annotations along with these if you so desire.
    See :ref:`msg_annotations` for more information about that.

.. py:attribute:: Pyro4.current_context.correlation_id

    (:py:class:`uuid.UUID`, optional)  correlation id of the current request / response.
    If you set this (in your client code) before calling a method on a Pyro proxy, Pyro will transfer the
    correlation id to the server context. If the server on their behalf invokes another
    Pyro method, the same correlation id will be passed along. This way it is possible
    to relate all remote method calls that originate from a single call.
    To make this work you'll have to set this to a new :py:class:`uuid.UUID` in your client
    code right before you call a Pyro method.
    Note that it is required that the correlation id is of type :py:class:`uuid.UUID`.
    Note that the HTTP gateway (see :ref:`http-gateway`) also creates a correlation id for
    every request, and will return it via the ``X-Pyro-Correlation-Id`` HTTP-header in the response.
    It will also accept this header optionally on a request in which case it will use the
    value from the header rather than generating a new id.


For an example of how this information can be retrieved, and how to set the ``correlation_id``,
see the :file:`callcontext` example.
See the :file:`usersession` example to learn how you could use it to build user-bound resource access without concurrency problems.


.. index:: annotations
.. _msg_annotations:

Message annotations
===================

.. sidebar:: advanced topic

    This is a very advanced/low-level Pyro topic.

Pyro's wire protocol allows for a very flexible messaging format by means of *annotations*.
Annotations are extra information chunks that are added to the pyro messages traveling
over the network. Pyro internally uses a couple of chunks to exchange extra data between a proxy
and a daemon: correlation ids (annotation ``CORR``) and hmac signatures
(annotation ``HMAC``). These chunk types are reserved and you should not touch them.
All other annotation types are free to use in your own code (and will be ignored
by Pyro itself). There's no limit on the number of annotations you can add to a message, but each
individual annotation cannot be larger than 64 Kb.

.. sidebar:: reserved annotation chunks

    The following annotation chunks are used by Pyro internally and should not be touched:
    ``CORR``, ``HMAC`` and ``STRM``.

An annotation is a low level datastructure (to optimize the generation of network messages):
a chunk identifier string of exactly 4 characters (such as "CODE"), and its value, a byte sequence.
If you want to put specific data structures into an annotation chunk value, you have to
encode them to a byte sequence yourself (ofcourse, you could utilize a Pyro serializer for this).
When processing a custom annotation, you have to decode it yourself as well.
Communicating annotations with Pyro is done via a normal dictionary of chunk id -> data bytes.
Pyro will take care of encoding this dictionary into the wire message and extracting it out of a response message.

*Customizing annotations:*

Adding your own annotations to messages is done by overriding the :py:meth:`Pyro4.core.Proxy._pyroAnnotations` method in your client code (proxy),
and/or the :py:meth:`Pyro4.core.Daemon.annotations` method in the server code (daemon).
If you override any of these methods, don't forget to call the original method and add to the dictionary returned from that,
rather than simply returning a new dictionary. Otherwise you will sabotage Pyro's internal annotations.

*Reacting on annotations:*

In the Daemon, you can use the :py:data:`Pyro4.current_context` to access the annotations of the message that was received.
See :ref:`current_context`.
In the client code you have to create a proxy subclass and override the method :py:meth:`Pyro4.core.Proxy._pyroResponseAnnotations`.
Pyro will call this method with the dictionary of any annotations received in a response message from the daemon,
and the message type identifier of the response message.

For an example of how you can work with custom message annotations, see the :py:mod:`callcontext` example.


.. index:: handshake

Connection handshake
====================

.. sidebar:: advanced topic

    This is a very advanced/low-level Pyro topic.

When a proxy is first connecting to a Pyro daemon, it exchanges a few messages to set up and validate the connection.
This is called the connection *handshake*. Part of it is the daemon returning the object's metadata (see :ref:`metadata`).
You can hook into this mechanism and influence the data that is initially exchanged during the connection setup,
and you can act on this data. You can disallow the connection based on this, for example.

You can set your own data on the proxy attribute :py:attr:`Pyro4.core.Proxy._pyroHandshake`. You can set any serializable object.
Pyro will send this as the handshake message to the daemon when the proxy tries to connect.
In the daemon, override the method :py:meth:`Pyro4.core.Daemon.validateHandshake` to customize/validate the connection setup.
This method receives the data from the proxy and you can either raise an exception if you don't want to allow the connection,
or return a result value if you are okay with the new connection. The result value again can be any serializable object.
This result value will be received back in the Proxy where you can act on it
if you subclass the proxy and override :py:meth:`Pyro4.core.Proxy._pyroValidateHandshake`.


For an example of how you can work with connections handshake validation, see the :py:mod:`handshake` example.
It implements a (bad!) security mechanism that requires the client to supply a "secret" password to be able to connect to the daemon.
