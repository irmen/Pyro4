***************************
Servers: publishing objects
***************************

This chapter explains how you write code that publishes objects to be remotely accessible.
These objects are then called *Pyro objects* and the program that provides them,
is often called a *server* program.

(The program that calls the objects is usually called the *client*.
Both roles can be mixed in a single program.)

Make sure you are familiar with Pyro's :ref:`keyconcepts` before reading on.

.. seealso::

    :doc:`config` for several config items that you can use to tweak various server side aspects.


.. _publish-objects:

Pyro Daemon: publishing Pyro objects
====================================

To publish a regular Python object and turn it into a Pyro object,
you have to tell Pyro about it. After that, your code has to tell Pyro to start listening for incoming
requests and to process them. Both are handled by the *Pyro daemon*.

In its most basic form, you create one or more objects that you want to publish as Pyro objects,
you create a daemon, register the object(s) with the daemon, and then enter the daemon's request loop::

    import Pyro4

    class MyPyroThing(object):
        pass

    thing=MyPyroThing()
    daemon=Pyro4.Daemon()
    uri=daemon.register(thing)
    print uri
    daemon.requestLoop()

After printing the uri, the server sits waiting for requests.
The uri that is being printed looks a bit like this: ``PYRO:obj_dcf713ac20ce4fb2a6e72acaeba57dfd@localhost:51850``
It can be used in a *client* program to create a proxy and access your Pyro object with.

.. note::
    You can publish any regular Python object as a Pyro object.
    However since Pyro adds a few Pyro-specific attributes to the object, you can't use:

    * types that don't allow custom attributes, such as the builtin types (``str`` and ``int`` for instance)
    * types with ``__slots__`` (a possible way around this is to add Pyro's custom attributes to your ``__slots__``, but that isn't very nice)


Oneliner Pyro object publishing
-------------------------------
Ok not really a one-liner, but one statement: use ``serveSimple`` to publish a dict of objects and start Pyro's request loop.
The code above could also be written as::

    import Pyro4

    class MyPyroThing(object):
        pass

    Pyro4.Daemon.serveSimple(
        {
            MyPyroThing(): None
        },
        ns=False, verbose=True)

Verbose is set to True because you want it to print out the generated random object uri, otherwise
there is no way to connect to your object. You can also choose to provide object names yourself,
to use or not use the name server, etc. See :py:func:`Pyro4.core.Daemon.serveSimple`.

Note that the amount of options you can provide is quite limited.
If you want to control the way the Pyro daemon is constructed, you have to do that by setting
the appropriate config options before calling ``serveSimple``.
Or you can create a daemon object yourself with the right arguments,
and pass that to ``serveSimple`` so that it doesn't create a default daemon itself.
Because they are so frequently used, ``serveSimple`` has a ``host`` and ``port`` parameter
that you can use to control the host and port of the daemon that it creates (useful if you
want to make it run on something else as localhost).

Creating a Daemon
-----------------
Pyro's daemon is :class:`Pyro4.core.Daemon` and you can also access it by its shortcut ``Pyro4.Daemon``.
It has a few optional arguments when you create it:


.. function:: Daemon([host=None, port=0, unixsocket=None, nathost=None, natport=None])

    Create a new Pyro daemon.

    :param host: the hostname or IP address to bind the server on. Default is ``None`` which means it uses the configured default (which is localhost).
    :type host: str or None
    :param port: port to bind the server on. Defaults to 0, which means to pick a random port.
    :type port: int
    :param unixsocket: the name of a Unix domain socket to use instead of a TCP/IP socket. Default is ``None`` (don't use).
    :type unixsocket: str or None
    :param nathost: hostname to use in published addresses (useful when running behind a NAT firewall/router). Default is ``None`` which means to just use the normal host.
                    For more details about NAT, see :ref:`nat-router`.
    :type host: str or None
    :param natport: port to use in published addresses (useful when running behind a NAT firewall/router)
    :type port: int


Registering objects
-------------------
Every object you want to publish as a Pyro object needs to be registered with the daemon.
You can let Pyro choose a unique object id for you, or provide a more readable one yourself.

.. method:: Daemon.register(obj [, objectId=None])

    Registers an object with the daemon to turn it into a Pyro object.

    :param obj: the object to register
    :param objectId: optional custom object id (must be unique). Default is to let Pyro create one for you.
    :type objectId: str or None
    :returns: an uri for the object
    :rtype: :class:`Pyro4.core.URI`

It is important to do something with the uri that is returned: it is the key to access the Pyro object.
You can save it somewhere, or perhaps print it to the screen.
The point is, your client programs need it to be able to access your object (they need to create a proxy with it).

Maybe the easiest thing is to store it in the Pyro name server.
That way it is almost trivial for clients to obtain the proper uri and connect to your object.
See :doc:`nameserver` for more information.

.. note::
    If you ever need to create a new uri for an object, you can use :py:meth:`Pyro4.core.Daemon.uriFor`.
    The reason this method exists on the daemon is because an uri contains location information and
    the daemon is the one that knows about this.

Intermission: Example 1: server and client not using name server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
A little code example that shows the very basics of creating a daemon and publishing a Pyro object with it.
Server code::

    import Pyro4

    class Thing(object):
        def method(self, arg):
            return arg*2

    # ------ normal code ------
    daemon = Pyro4.Daemon()
    uri = daemon.register(Thing())
    print "uri=",uri
    daemon.requestLoop()

    # ------ alternatively, using serveSimple -----
    Pyro4.Daemon.serveSimple(
        {
            Thing(): None
        },
        ns=False, verbose=True)

Client code example to connect to this object::

    import Pyro4
    # use the URI that the server printed:
    uri = "PYRO:obj_b2459c80671b4d76ac78839ea2b0fb1f@localhost:49383"
    thing = Pyro4.Proxy(uri)
    print thing.method(42)   # prints 84

With correct additional parameters --described elsewhere in this chapter-- you can control on which port the daemon is listening,
on what network interface (ip address/hostname), what the object id is, etc.

Intermission: Example 2: server and client, with name server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
A little code example that shows the very basics of creating a daemon and publishing a Pyro object with it,
this time using the name server for easier object lookup.
Server code::

    import Pyro4

    class Thing(object):
        def method(self, arg):
            return arg*2

    # ------ normal code ------
    daemon = Pyro4.Daemon()
    ns = Pyro4.locateNS()
    uri = daemon.register(Thing())
    ns.register("mythingy", uri)
    daemon.requestLoop()

    # ------ alternatively, using serveSimple -----
    Pyro4.Daemon.serveSimple(
        {
            Thing(): "mythingy"
        },
        ns=True, verbose=True)

Client code example to connect to this object::

    import Pyro4
    thing = Pyro4.Proxy("PYRONAME:mythingy")
    print thing.method(42)   # prints 84

Unregistering objects
---------------------
When you no longer want to publish an object, you need to unregister it from the daemon:

.. method:: Daemon.unregister(objectOrId)

    :param objectOrId: the object to unregister
    :type objectOrId: object itself or its id string


Running the request loop
------------------------
Once you've registered your Pyro object you'll need to run the daemon's request loop to make
Pyro wait for incoming requests.

.. method:: Daemon.requestLoop([loopCondition])

    :param loopCondition: optional callable returning a boolean, if it returns False the request loop will be aborted and the call returns

This is Pyro's event loop and it will take over your program until it returns (it might never.)
If this is not what you want, you can control it a tiny bit with the ``loopCondition``, or read the next paragraph.

Integrating Pyro in your own event loop
---------------------------------------
If you want to use a Pyro daemon in your own program that already has an event loop (aka main loop),
you can't simply call ``requestLoop`` because that will block your program.
A daemon provides a few tools to let you integrate it into your own event loop:

* :py:attr:`Pyro4.core.Daemon.sockets` - list of all socket objects used by the daemon, to inject in your own event loop
* :py:meth:`Pyro4.core.Daemon.events` - method to call from your own event loop when Pyro needs to process requests. Argument is a list of sockets that triggered.

For more details and example code, see the :file:`eventloop` and :file:`gui_eventloop` examples.
They show how to use Pyro including a name server, in your own event loop, and also possible ways
to use Pyro from within a GUI program with its own event loop.


Cleaning up
-----------
To clean up the daemon itself (release its resources) either use the daemon object
as a context manager in a ``with`` statement, or manually call :py:meth:`Pyro4.core.Daemon.close`.


Autoproxying
============
Pyro will automatically take care of any Pyro objects that you pass around through remote method calls.
It will replace them by a proxy automatically, so the receiving side can call methods on it and be
sure to talk to the remote object instead of a local copy. There is no need to create a proxy object manually.
All you have to do is to register the new object with the appropriate daemon::

    def some_pyro_method(self):
        thing=SomethingNew()
        self._pyroDaemon.register(thing)
        return thing    # just return it, no need to return a proxy

This feature can be enabled or disabled by a config item, see :doc:`config`.
(it is on by default). If it is off, a copy of the object itself is returned,
and the client won't be able to interact with the actual new Pyro object in the server.
There is a :file:`autoproxy` example that shows the use of this feature,
and several other examples also make use of it.

Server types and Object concurrency model
=========================================
Pyro supports multiple server types (the way the Daemon listens for requests). Select the
desired type by setting the ``SERVERTYPE`` config item. It depends very much on what you
are doing in your Pyro objects what server type is most suitable. For instance, if your Pyro
object does a lot of I/O, it may benefit from the parallelism provided by the thread pool server.
However if it is doing a lot of CPU intensive calculations, the multiplexed server may be more
appropriate. If in doubt, go with the default setting.

#. threaded server (servertype ``"threaded"``, this is the default)
    This server uses a thread pool to handle incoming proxy connections.
    The size of the pool is configurable via various config items.
    Every proxy on a client that connects to the daemon will be assigned to a thread to handle
    the remote method calls. This way multiple calls can be processed concurrently.
    This means your Pyro object must be *thread-safe*! If you access a shared resource from
    your Pyro object you may need to take thread locking measures such as using Queues.
    If the thread pool is too small for the number of proxy connections, new proxy connections will
    be put to wait until another proxy disconnects from the server.

#. multiplexed server (servertype ``"multiplex"``)
    This server uses a select (or poll, if available) based connection multiplexer to process
    all remote method calls sequentially. No threads are used in this server. It means
    only one method call is running at a time, so if it takes a while to complete, all other
    calls are waiting for their turn (even when they are from different proxies).

.. note::
    If the ``ONEWAY_THREADED`` config item is enabled (it is by default), *oneway* method calls will
    be executed in a separate worker thread, regardless of the server type you're using.

.. note::
    It must be pretty obvious but the following is a very important concept so it is repeated
    once more to be 100% clear:
    Currently, you register *objects* with Pyro, not *classes*. This means remote method calls
    to a certain Pyro object always run on the single instance that you registered with Pyro.


Other features
==============

Attributes added to Pyro objects
--------------------------------
The following attributes will be added your object if you register it as a Pyro object:

* ``_pyroId`` - the unique id of this object (a ``str``)
* ``_pyroDaemon`` - a reference to the :py:class:`Pyro4.core.Daemon` object that contains this object

Even though they start with an underscore (and are private, in a way),
you can use them as you so desire. As long as you don't modify them!
The daemon reference for instance is useful to register newly created objects with,
to avoid the need of storing a global daemon object somewhere.


These attributes will be removed again once you unregister the object.

Network adapter binding
-----------------------

All Pyro daemons bind on localhost by default. This is because of security reasons.
This means only processes on the same machine have access to your Pyro objects.
If you want to make them available for remote machines, you'll have to tell Pyro on what
network interface address it must bind the daemon.

.. warning::
    Read chapter :doc:`security` before exposing Pyro objects to remote machines!

There are a few ways to tell Pyro what network address it needs to use.
You can set a global config item ``HOST``, or pass a ``host`` parameter to the constructor of a Daemon,
or use a command line argument if you're dealing with the name server.
For more details, refer to the chapters in this manual about the relevant Pyro components.

Pyro provides a couple of utility functions to help you with finding the appropriate IP address
to bind your servers on if you want to make them publicly accessible:

* :py:func:`Pyro4.socketutil.getMyIpAddress`
* :py:func:`Pyro4.socketutil.getInterfaceAddress`


Daemon Pyro interface
---------------------
A rather interesting aspect of Pyro's Daemon is that it (partly) is a Pyro object itself.
This means it exposes a couple of remote methods that you can also invoke yourself if you want.
The object exposed is :class:`Pyro4.core.DaemonObject` (as you can see it is a bit limited still).

You access this object by creating a proxy for the ``"Pyro.Daemon"`` object. That is a reserved
object name. You can use it directly but it is preferable to use the constant
``Pyro4.constants.DAEMON_NAME``. An example follows that accesses the daemon object from a running name server::

    >>> import Pyro4
    >>> daemon=Pyro4.Proxy("PYRO:"+Pyro4.constants.DAEMON_NAME+"@localhost:9090")
    >>> daemon.ping()
    >>> daemon.registered()
    ['Pyro.NameServer', 'Pyro.Daemon']

