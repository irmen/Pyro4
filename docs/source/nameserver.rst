.. index:: Name Server

.. _name-server:

***********
Name Server
***********

The Pyro Name Server is a tool to help keeping track of your objects in your network.
It is also a means to give your Pyro objects logical names instead of the need to always
know the exact object name (or id) and its location.

Pyro will name its objects like this::

    PYRO:obj_dcf713ac20ce4fb2a6e72acaeba57dfd@localhost:51850
    PYRO:custom_name@localhost:51851

It's either a generated unique object id on a certain host, or a name you chose yourself.
But to connect to these objects you'll always need to know the exact object name or id and
the exact hostname and port number of the Pyro daemon where the object is running.
This can get tedious, and if you move servers around (or Pyro objects) your client programs
can no longer connect to them until you update all URIs.

Enter the *name server*.
This is a simple phone-book like registry that maps logical object names to their corresponding URIs.
No need to remember the exact URI anymore. Instead, you can ask the name server to look it up for
you. You only need to give it the logical object name.

.. note:: Usually you only need to run *one single instance* of the name server in your network.
    You can start multiple name servers but they are unconnected; you'll end up with a partitioned name space.


**Example scenario:**
Assume you've got a document archive server that publishes a Pyro object with several archival related methods in it.
This archive server can register this object with the name server, using a logical name such as
"Department.ArchiveServer". Any client can now connect to it using only the name "Department.ArchiveServer".
They don't need to know the exact Pyro id and don't even need to know the location.
This means you can move the archive server to another machine and as long as it updates its record in the
name server, all clients won't notice anything and can keep on running without modification.


.. index:: starting the name server
    double: name server; command line

.. _nameserver-nameserver:

Starting the Name Server
========================

The easiest way to start a name server is by using the command line tool.

synopsys: :command:`python -m Pyro4.naming [options]` (or simply: :command:`pyro4-ns [options]`)


Starts the Pyro Name Server. It can run without any arguments but there are several that you
can use, for instance to control the hostname and port that the server is listening on.
A short explanation of the available options can be printed with the help option.
When it starts, it prints a message similar to this ('neptune' is the hostname of the machine it is running on)::

    $ pyro4-ns -n neptune
    Broadcast server running on 0.0.0.0:9091
    NS running on neptune:9090 (192.168.1.100)
    URI = PYRO:Pyro.NameServer@neptune:9090

As you can see it prints that it started a broadcast server (and its location),
a name server (and its location), and it also printed the URI that clients can use
to access it directly.

The nameserver uses a fast but volatile in-memory database by default. With a command line argument
you can select a persistent storage mechanism (see below). If you're using that, your registrations
will not be lost when the nameserver stops/restarts. The server will print the number of
existing registrations at startup time if it discovers any.


.. note::
    Pyro by default binds its servers on localhost which means you cannot reach them
    from another machine on the network. This behavior also applies to the name server.
    If you want to be able to talk to the name server from other machines, you have to
    explicitly provide a hostname to bind on.

There are several command line options for this tool:

.. program:: Pyro4.naming

.. option:: -h, --help

   Print a short help message and exit.

.. option:: -n HOST, --host=HOST

   Specify hostname or ip address to bind the server on.
   The default is localhost, note that your name server will then not be visible from the network
   If the server binds on localhost, *no broadcast responder* is started either.
   Make sure to provide a hostname or ip address to make the name server reachable from other machines, if you want that.

.. option:: -p PORT, --port=PORT

   Specify port to bind server on (0=random).

.. option:: -u UNIXSOCKET, --unixsocket=UNIXSOCKET

   Specify a Unix domain socket name to bind server on, rather than a normal TCP/IP socket.

.. option:: --bchost=BCHOST

   Specify the hostname or ip address to bind the broadcast responder on.
   Note: if the hostname where the name server binds on is localhost (or 127.0.x.x),
   no broadcast responder is started.

.. option:: --bcport=BCPORT

   Specify the port to bind the broadcast responder on (0=random).

.. option:: --nathost=NATHOST

   Specify the external host name to use in case of NAT

.. option:: --natport=NATPORT

   Specify the external port use in case of NAT

.. option:: -s STORAGE, --storage=STORAGE

   Specify the storage mechanism to use. You have several options:

    - ``memory`` - fast, volatile in-memory database. This is the default.
    - ``dbm:dbfile`` - dbm-style persistent database table. Provide the filename to use.
    - ``sql:sqlfile`` - sqlite persistent database. Provide the filename to use.

.. option:: -x, --nobc

   Don't start a broadcast responder. Clients will not be able to use the UDP-broadcast lookup
   to discover this name server.
   (The broadcast responder listens to UDP broadcast packets on the local network subnet,
   to signal its location to clients that want to talk to the name server)

.. option:: -k, --key

   Specify hmac key to use.


Starting the Name Server from within your own code
==================================================

Another way to start up a name server is by doing it from within your own code.
This is more complex than simply launching it via the command line tool,
because you have to integrate the name server into the rest of your program (perhaps you need to merge event loops?).
For your convenience, two helper functions are available to create a name server yourself:
:py:func:`Pyro4.naming.startNS` and :py:func:`Pyro4.naming.startNSloop`.
Look at the :file:`eventloop` example to see how you can use this.

**Custom storage mechanism:**
The utility functions allow you to specify a custom storage mechanism (via the ``storage`` parameter).
By default the in memory storage :py:class:`Pyro4.naming.MemoryStorage` is used.
In the :py:mod:`Pyro4.naming_storage` module you can find the two other implementations (for the dbm and
for the sqlite storage). You could also build your own, as long as it has the same interface.



.. index::
    double: name server; configuration items

Configuration items
===================
There are a couple of config items related to the nameserver.
They are used both by the name server itself (to configure the values it will use to start
the server with), and the client code that locates the name server (to give it optional hints where
the name server is located). Often these can be overridden with a command line option or with a method parameter in your code.

================== ===========
Configuration item description
================== ===========
HOST               hostname that the name sever will bind on (being a regular Pyro daemon).
NS_HOST            the hostname or ip address of the name server. Used for locating in clients only.
NS_PORT            the port number of the name server. Used by the server and for locating in clients.
NS_BCHOST          the hostname or ip address of the name server's broadcast responder. Used only by the server.
NS_BCPORT          the port number of the name server's broadcast responder. Used by the server and for locating in clients.
NATHOST            the external hostname in case of NAT. Used only by the server.
NATPORT            the external port in case of NAT. Used only by the server.
================== ===========


.. index::
    double: name server; name server control

.. _nameserver-nsc:

Name server control tool
========================
The name server control tool (or 'nsc') is used to talk to a running name server and perform
diagnostic or maintenance actions such as querying the registered objects, adding or removing
a name registration manually, etc.

synopsis: :command:`python -m Pyro4.nsc [options] command [arguments]` (or simply: :command:`pyro4-nsc [options] command [arguments]`)


.. program:: Pyro4.nsc

.. option:: -h, --help

   Print a short help message and exit.

.. option:: -n HOST, --host=HOST

   Provide the hostname or ip address of the name server.
   The default is to do a broadcast lookup to search for a name server.

.. option:: -p PORT, --port=PORT

   Provide the port of the name server, or its broadcast port if you're doing a broadcast lookup.

.. option:: -u UNIXSOCKET, --unixsocket=UNIXSOCKET

   Provide the Unix domain socket name of the name server, rather than a normal TCP/IP socket.

.. option:: -k, --key

   Specify hmac key to use.

.. option:: -v, --verbose

   Print more output that could be useful.


The available commands for this tool are:

list : list [prefix]
  List all objects registered in the name server. If you supply a prefix,
  the list will be filtered to show only the objects whose name starts with the prefix.

listmatching : listmatching pattern
  List only the objects with a name matching the given regular expression pattern.

lookup : lookup name
  Looks up a single name registration and prints the uri.

register : register name uri
  Registers a name to the given Pyro object :abbr:`URI (universal resource identifier)`.

remove : remove name
  Removes the entry with the exact given name from the name server.

removematching : removematching pattern
  Removes all entries matching the given regular expression pattern.

ping
  Does nothing besides checking if the name server is running and reachable.


Example::

  $ pyro4-nsc ping
  Name server ping ok.

  $ pyro4-nsc list Pyro
  --------START LIST - prefix 'Pyro'
  Pyro.NameServer --> PYRO:Pyro.NameServer@localhost:9090
  --------END LIST - prefix 'Pyro'


.. index::
    double: name server; locating the name server

Locating the Name Server and using it in your code
==================================================
The name server is a Pyro object itself, and you access it through a normal Pyro proxy.
The object exposed is :class:`Pyro4.naming.NameServer`.
Getting a proxy for the name server is done using the following function:
:func:`Pyro4.naming.locateNS` (also available as :func:`Pyro4.locateNS`).

.. index::
    double: name server; broadcast lookup

By far the easiest way to locate the Pyro name server is by using the broadcast lookup mechanism.
This goes like this: you simply ask Pyro to look up the name server and return a proxy for it.
It automatically figures out where in your subnet it is running by doing a broadcast and returning
the first Pyro name server that responds. The broadcast is a simple UDP-network broadcast, so this
means it usually won't travel outside your network subnet (or through routers) and your firewall
needs to allow UDP network traffic.

There is a config item ``BROADCAST_ADDRS`` that contains a comma separated list of the broadcast
addresses Pyro should use when doing a broadcast lookup. Depending on your network configuration,
you may have to change this list to make the lookup work. It could be that you have to add the
network broadcast address for the specific network that the name server is located on.

.. note::
    You can only talk to a name server on a different machine if it didn't bind on localhost (that
    means you have to start it with an explicit host to bind on). The broadcast lookup mechanism
    only works in this case as well -- it doesn't work with a name server that binds on localhost.
    For instance, the name server started as an example in :ref:`nameserver-nameserver` was told to
    bind on the host name 'neptune' and it started a broadcast responder as well.
    If you use the default host (localhost) a broadcast responder will not be created.

Normally, all name server lookups are done this way. In code, it is simply calling the
locator function without any arguments.
If you want to circumvent the broadcast lookup (because you know the location of the
server already, somehow) you can specify the hostname.
As soon as you provide a specific hostname to the name server locator (by using a host argument
to the ``locateNS`` call, or by setting the ``NS_HOST`` config item, etc) it will no longer use
a broadcast too try to find the name server.

.. function:: locateNS([host=None, port=None, broadcast=True, hmac_key=key])

    Get a proxy for a name server somewhere in the network.
    If you're not providing host or port arguments, the configured defaults are used.
    Unless you specify a host, a broadcast lookup is done to search for a name server.
    (api reference: :py:func:`Pyro4.naming.locateNS`)

    :param host: the hostname or ip address where the name server is running.
        Default is ``None`` which means it uses a network broadcast lookup.
        If you specify a host, no broadcast lookup is performed.
    :param port: the port number on which the name server is running.
        Default is ``None`` which means use the configured default.
        The exact meaning depends on whether the host parameter is given:

        * host parameter given: the port now means the actual name server port.
        * host parameter not given: the port now means the broadcast port.
    :param broadcast: should a broadcast be used to locate the name server, if
        no location is specified? Default is True.
    :param hmac_key: optional hmac key to use


.. index:: PYRONAME protocol type
.. _nameserver-pyroname:

The 'magical' PYRONAME protocol type
====================================
To create a proxy and connect to a Pyro object, Pyro needs an URI so it can find the object.
Because it is so convenient, the name server logic has been integrated into Pyro's URI mechanism
by means of the special ``PYRONAME`` protocol type (rather than the normal ``PYRO`` protocol type).
This protocol type tells Pyro to treat the URI as a logical object name instead, and Pyro will
do a name server lookup automatically to get the actual object's URI. The form of a PYRONAME uri
is very simple::

    PYRONAME:some_logical_object_name
    PYRONAME:some_logical_object_name@nshostname           # with optional host name
    PYRONAME:some_logical_object_name@nshostname:nsport    # with optional host name + port

where "some_logical_object_name" is the name of a registered Pyro object in the name server.
When you also provide the ``nshostname`` and perhaps even ``nsport`` parts in the uri, you tell Pyro to look
for the name server on that specific location (instead of relying on a broadcast lookup mechanism).
(You can achieve more or less the same by setting the ``NS_HOST`` and ``NS_PORT`` config items)

All this means that instead of manually resolving objects like this::

    nameserver=Pyro4.locateNS()
    uri=nameserver.lookup("Department.BackupServer")
    proxy=Pyro4.Proxy(uri)
    proxy.backup()

you can write this instead::

    proxy=Pyro4.Proxy("PYRONAME:Department.BackupServer")
    proxy.backup()

An additional benefit of using a PYRONAME uri in a proxy is that the proxy isn't strictly
tied to a specific object on a specific location. This is useful in scenarios where the server
objects might move to another location, for instance when a disconnect/reconnect occurs.
See the :file:`autoreconnect` example for more details about this.

.. note::
    Pyro has to do a lookup every time it needs to connect one of these PYRONAME uris.
    If you connect/disconnect many times or with many different objects,
    consider using PYRO uris (you can type them directly or create them by resolving as explained in the
    following paragraph) or call :meth:`Pyro4.core.Proxy._pyroBind()` on the proxy to
    bind it to a fixed PYRO uri instead.


.. index:: resolving object names, PYRONAME protocol type

Resolving object names
======================
'Resolving an object name' means to look it up in the name server's registry and getting
the actual URI that belongs to it (with the actual object name or id and the location of
the daemon in which it is running). This is not normally needed in user code (Pyro takes
care of it automatically for you), but it can still be useful in certain situations.

So, resolving a logical name can be done in several ways:

- let Pyro do it for you, for instance simply pass a ``PYRONAME`` URI to the proxy constructor
- use a ``PYRONAME`` URI and resolve it using the ``resolve`` utility function (see below)
- obtain a name server proxy and use its ``lookup`` method;  ``uri = ns.lookup("objectname")``

You can resolve a ``PYRONAME`` URI explicitly using the following utility function:
:func:`Pyro4.naming.resolve` (also available as :func:`Pyro4.resolve`), which goes like this:

.. function:: resolve(uri [, hmac_key=None])

    Finds a name server, and use that to resolve a PYRONAME uri into the direct PYRO uri pointing to the named object.
    If uri is already a PYRO uri, it is returned unmodified.
    *Note:* if you need to resolve more than a few names, consider using the name server directly instead of
    repeatedly calling this function, to avoid the name server lookup overhead from each call.

    :param uri: PYRONAME uri that you want to resolve
    :type uri: string or :class:`Pyro4.core.URI`
    :param hmac_key: optional hmac key to use

.. index::
    double: name server; registering objects
    double: name server; unregistering objects

.. _nameserver-registering:

Registering object names
========================
'Registering an object' means that you associate the URI with a logical name, so that
clients can refer to your Pyro object by using that name.
Your server has to register its Pyro objects with the name server. It first registers an
object with the Daemon, gets an URI back, and then registers that URI in the name server using
the following method on the name server proxy:

.. py:method:: register(name, uri, safe=False)

    Registers an object (uri) under a logical name in the name server.

    :param name: logical name that the object will be known as
    :type name: string
    :param uri: the URI of the object (you get it from the daemon)
    :type uri: string or :class:`Pyro4.core.URI`
    :param safe: normally registering the same name twice silently overwrites the old registration. If you set safe=True, the same name cannot be registered twice.
    :type safe: bool

You can unregister objects as well using the :py:meth:`unregister` method.


.. index:: scaling Name Server connections

Free connections quickly (or: scaling the Name Server)
======================================================
By default the Name server uses a Pyro socket server based on whatever configuration is the default.
Usually that will be a threadpool based server with a limited pool size. If more clients connect to
the name server than the pool size allows, new connections block (and may lock up your system if
no existing connections are freed).

It is suggested you apply the following pattern when using the name server in your code:

#. obtain a proxy for the NS
#. look up the stuff you need, store it
#. free the NS proxy (See :ref:`client_cleanup`)
#. use the uri's/proxies you've just looked up

This makes sure your client code doesn't consume resources in the name server for an excessive amount of time,
and more importantly, frees up the limited connection pool to let other clients get their turn.
If you have a proxy to the name server and you let it live for too long, it may eventually deny
other clients access to the name server because its connection pool is exhausted. If you don't need
the proxy anymore, make sure to free it up.

There are a number of things you can do to improve the matter on the side of the Name Server itself.
You can control its behavior by setting certain Pyro config items before starting the server:

- You can set ``SERVERTYPE=multiplex`` to create a server that doesn't use a limited connection (thread) pool,
  but multiplexes as many connections as the system allows. However, the actual calls to the server must
  now wait on eachother to complete before the next call is processed. This may impact performance in other ways.
- You can set ``THREADPOOLSIZE`` to a larger number as the default. This extends the connection pool of
  the server but it is still limited by an upper bound ofcourse.
- You can set ``COMMTIMEOUT`` to a certain value, which frees up unused connections after the given time.
  But the client code may now crash with a TimeoutError or ConnectionClosedError when it tries to use a
  proxy it obtained earlier. (You can use Pyro's autoreconnect feature to work around this but it makes
  the code more complex)


.. index::
    double: name server; pickle

.. _nameserver-pickle:

Using the name server with pickle serializer
============================================
If you find yourself in the unfortunate situation where you absolutely have to use the pickle serializer, you have to
pay attention when also using the name server.
Because pickle is disabled by default, the name server will not reply to messages from clients
that are using the pickle serializer, unless you enable pickle in the name server as well.

The symptoms are usually that your client code seems unable to contact the name server::

    Pyro4.errors.NamingError: Failed to locate the nameserver

The name server will show a user warning message on the console::

    Pyro protocol error occurred: message used serializer that is not accepted

And if you enable logging for the name server you will likely see in its logfile::

    accepted serializers: {'json', 'marshal', 'serpent'}
    ...
    ...
    Pyro4.errors.ProtocolError: message used serializer that is not accepted: 4

The way to solve this is to stop using the pickle serializer, or if you must use it,
tell the name server that it is okay to accept it. You do that by
setting the ``SERIALIZERS_ACCEPTED`` config item to a set of serializers that includes pickle,
and then restart the name server. For instance::

    $ export PYRO_SERIALIZERS_ACCEPTED=serpent,json,marshal,pickle
    $ pyro4-ns

If you enable logging you will then see that the name server says that pickle is among the accepted serializers.

.. index:: Name Server API

Other methods in the Name Server API
====================================
The name server has a few other methods that might be useful at times.
For instance, you can ask it for a list of all registered objects.
Because the name server itself is a regular Pyro object, you can access its methods
through a regular Pyro proxy, and refer to the description of the exposed class to
see what methods are available: :class:`Pyro4.naming.NameServer`.
