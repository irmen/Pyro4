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


.. _nameserver-nameserver:

Starting the Name Server
========================

The easiest way to start a name server is by using the command line tool.

synopsys: :command:`python -m Pyro4.naming [options]`

Starts the Pyro Name Server. It can run without any arguments but there are several that you
can use, for instance to control the hostname and port that the server is listening on.
A short explanation of the available options can be printed with the help option.
When it starts, it prints a message similar to this::

    $ python -m Pyro4.naming -n neptune
    Broadcast server running on 0.0.0.0:9091
    NS running on neptune:9090 (192.168.1.100)
    URI = PYRO:Pyro.NameServer@neptune:9090

As you can see it prints that it started a broadcast server (and its location),
a name server (and its location), and it also printed the URI that clients can use
to access it directly. These things will be explained below.

There are several command line options:

.. program:: Pyro4.naming

.. option:: -h, --help

   Print a short help message and exit.

.. option:: -n HOST, --host=HOST

   Specify hostname or ip address to bind the server on.
   The default is localhost.
   If the server binds on localhost, *no broadcast responder* is started.

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

.. option:: -x, --nobc

   Don't start a broadcast responder.


Another way is doing it from within your own code.
This is much more complex because you will have to integrate the name server
into the rest of your program (perhaps you need to merge event loops).
A helper function is available to create it in your program: :py:func:`Pyro4.naming.startNS`.
Look at the :file:`eventloop` example to see how you can use this.

Configuration items
===================
There are a couple of config items related to the nameserver.
They are used both by the name server itself (to configure the values it will use to start
the server with), and the client code that locates the name server (to give it optional hints where
the name server is located). Often these can be overridden with a command line option or with a method parameter in your code.

================== ===========
Configuration item description
================== ===========
NS_HOST            the hostname or ip address of the name server
NS_PORT            the port number of the name server
NS_BCHOST          the hostname or ip address of the name server's broadcast responder
NS_BCPORT          the port number of the name server's broadcast responder
NATHOST            the external hostname in case of NAT
NATPORT            the external port in case of NAT
================== ===========


.. _nameserver-nsc:

Name server control tool
========================
The name server control tool (or 'nsc') is used to talk to a running name server and perform
diagnostic or maintenance actions such as querying the registered objects, adding or removing
a name registration manually, etc.

synopsis: :command:`python -m Pyro4.nsc [options] command [arguments]`


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

.. option:: -v, --verbose

   Print more output that could be useful.


The available commands for this tool are:

list : list [prefix]
  List all objects registered in the name server. If you supply a prefix,
  the list will be filtered to show only the objects whose name starts with the prefix.

listmatching : listmatching pattern
  List only the objects with a name matching the given regular expression pattern.

register : register name uri
  Registers a name to the given Pyro object :abbr:`URI (universal resource identifier)`.

remove : remove name
  Removes the entry with the exact given name from the name server.

removematching : removematching pattern
  Removes all entries matching the given regular expression pattern.

ping
  Does nothing besides checking if the name server is running and reachable.


Example::

  $ python -m Pyro4.nsc ping
  Name server ping ok.

  $ python -m Pyro4.nsc list Pyro
  --------START LIST - prefix 'Pyro'
  Pyro.NameServer --> PYRO:Pyro.NameServer@localhost:9090
  --------END LIST - prefix 'Pyro'


Locating the Name Server and using it in your code
==================================================
The name server is a Pyro object itself, and you access it through a normal Pyro proxy.
The object exposed is :class:`Pyro4.naming.NameServer`.
Getting a proxy for the name server is done using the following function:
:func:`Pyro4.naming.locateNS` (also available as :func:`Pyro4.locateNS`).

By far the easiest way to locate the Pyro name server is by using the broadcast lookup mechanism.
This goes like this: you simply ask Pyro to look up the name server and return a proxy for it.
It automatically figures out where in your subnet it is running by doing a broadcast and returning
the first Pyro name server that responds.

There is a config item ``BROADCAST_ADDRS`` that contains a comma separated list of the broadcast
addresses Pyro should use when doing a broadcast lookup. Depending on your network configuration,
you may have to change this list to make the lookup work. It could be that you have to add the
network broadcast address for the specific network that the name server is located on.

.. note::
    Broadcast lookup only works if you started a name server that didn't bind on localhost.
    For instance, the name server started as an example in :ref:`nameserver-nameserver` was told to
    bind on the host name 'neptune' and it started a broadcast responder as well.
    If you use the default host (localhost) no broadcast responder can be created.

Normally, all name server lookups are done this way. In code, it is simply calling the
locator function without any arguments.
If you want to circumvent the broadcast lookup (because you know the location of the
server already, somehow) you can specify the hostname.

.. function:: locateNS([host=None, port=None])

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



The 'magical' PYRONAME protocol type
====================================
To create a proxy and connect to a Pyro object, Pyro needs an URI so it can find the object.
Because it is so convenient, the name server logic has been integrated into Pyro's URI mechanism
by means of the special ``PYRONAME`` protocol type (rather than the normal ``PYRO`` protocol type).
This protocol type tells Pyro to treat the URI as a logical object name instead, and Pyro will
do a name server lookup automatically to get the actual object's URI. The form of a PYRONAME uri
is very simple: ``PYRONAME:some_logical_object_name``, where
"some_logical_object_name" is the name of a registered Pyro object in the name server.
This means that instead of manually resolving objects like this::

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


Resolving object names
======================
'Resolving an object name' means to look it up in the name server's registry and getting
the actual URI that belongs to it (with the actual object name or id and the location of
the daemon in which it is running). This is not normally needed in user code (Pyro takes
care of it automatically for you), but it can still be useful in certain situations.

Resolving a logical name is usually done by getting a name server proxy and using the ``lookup`` method.
This returns the URI object. You can also resolve a ``PYRONAME`` URI using the following utility function:
:func:`Pyro4.naming.resolve` (also available as :func:`Pyro4.resolve`), which goes like this:

.. function:: resolve(uri)

    Finds a name server, and use that to resolve a PYRONAME uri into the direct PYRO uri pointing to the named object.
    If uri is already a PYRO uri, it is returned unmodified.
    *Note:* if you need to resolve more than a few names, consider using the name server directly instead of
    repeatedly calling this function, to avoid the name server lookup overhead from each call.

    :param uri: PYRONAME uri that you want to resolve
    :type uri: string or :class:`Pyro4.core.URI`

