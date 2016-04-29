.. index:: server code

*****************************
Servers: hosting Pyro objects
*****************************

This chapter explains how you write code that publishes objects to be remotely accessible.
These objects are then called *Pyro objects* and the program that provides them,
is often called a *server* program.

(The program that calls the objects is usually called the *client*.
Both roles can be mixed in a single program.)

Make sure you are familiar with Pyro's :ref:`keyconcepts` before reading on.

.. seealso::

    :doc:`config` for several config items that you can use to tweak various server side aspects.


.. index::
    single: decorators
    single: @Pyro4.expose
    single: @Pyro4.oneway
    single: REQUIRE_EXPOSE
    double: decorator; expose
    double: decorator; oneway

.. _decorating-pyro-class:

Creating a Pyro class and using the Pyro4 decorators
====================================================

**What is exposed by default, and the REQUIRE_EXPOSE config item**

Pyro's default behavior is to expose *all* methods of your class
(unless they are private, which means the name is starting with a single or double underscore -- with an exception of the special 'dunder' names with double underscores such as ``__len__``).
You don't have to do anything to your server side code to make it available to remote calls, apart from
registering the class with a Pyro daemon ofcourse.
This is for backward compatibility and ease-of-use reasons.

If you don't like this (maybe security reasons) or simply want to expose only a part of your class to the remote world,
you can tell Pyro to *require* the explicit use of the ``@expose`` decorator (described below) on the items that you want to make
available for remote access. If something doesn't have the decorator, it is not remotely accessible.
This behavior can be chosen by setting the ``REQUIRE_EXPOSE`` config item to ``True``. It is set to ``False`` by default,
because of backwards compatibility reasons.

**the @expose decorator: exposing classes, methods and attributes for remote access**

The ``@Pyro4.expose`` decorator lets you mark the following items to be available for remote access:

- methods (including classmethod and staticmethod. You cannot expose a private method, i.e. name starting with underscore). You *can* expose a 'dunder' method with double underscore such as ``__len__``. There is a list of dunder methods that will never be remoted though (because they are essential to let the Pyro proxy function correctly).
- properties (will be available as remote attributes on the proxy)
- classes (exposing a class has the effect of exposing every method and property of the class automatically)

Remember that you must set the ``REQUIRE_EXPOSE`` config item to ``True`` to let all this have any effect!
Also because it is not possible to decorate attributes on a class, it is required to provide a @property for them
and decorate that with ``@expose``, if you want to provide a remotely accessible attribute.

Here's a piece of example code that shows how a partially exposed Pyro class may look like::

    import Pyro4

    Pyro4.config.REQUIRE_EXPOSE = True      # make @expose do something

    class PyroService(object):

        value = 42                  # not exposed

        def __dunder__(self):       # exposed
            pass

        def _private(self):         # not exposed
            pass

        def __private(self):        # not exposed
            pass

        @Pyro4.expose
        def get_value(self):        # exposed
            return self.value

        @Pyro4.expose
        @property
        def attr(self):             # exposed as 'proxy.attr' remote attribute
            return self.value

        @Pyro4.expose
        @attr.setter
        def attr(self, value):      # exposed as 'proxy.attr' writable
            self.value = value


.. index:: oneway decorator

**Specifying one-way methods using the @Pyro4.oneway decorator:**

You decide on the class of your Pyro object on the server, what methods are to be called as one-way.
You use the ``@Pyro4.oneway`` decorator on these methods to mark them for Pyro.
When the client proxy connects to the server it gets told automatically what methods are one-way,
you don't have to do anything on the client yourself. Any calls your client code makes on the proxy object
to methods that are marked with ``@Pyro4.oneway`` on the server, will happen as one-way calls::

    import Pyro4

    class PyroService(object):

        def normal_method(self, args):
            result = do_long_calculation(args)
            return result

        @Pyro4.oneway
        def oneway_method(self, args):
            result = do_long_calculation(args)
            # no return value, cannot return anything to the client


See :ref:`oneway-calls-client` for the documentation about how client code handles this.
See the :file:`oneway` example for some code that demonstrates the use of oneway methods.


.. index:: publishing objects

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
        # ... methods that can be called go here...
        pass

    thing = MyPyroThing()
    daemon = Pyro4.Daemon()
    uri = daemon.register(thing)
    print(uri)
    daemon.requestLoop()

When publising objects directly like this,  Pyro will use that single
object to handle *all* remote method calls. You may need to consider what this
means when your object is called concurrently from multiple threads,
see :ref:`object_concurrency`.

There's another more advanced way to register objects with Pyro, that lets you control more precisely
when and for how long Pyro will create an instance of your Pyro class. See :ref:`server-instancemode` below,
for more details.

Anyway, when you run the code printed above, the uri will be printed and the server sits waiting for requests.
The uri that is being printed looks a bit like this: ``PYRO:obj_dcf713ac20ce4fb2a6e72acaeba57dfd@localhost:51850``
Client programs use these uris to access the specific Pyro objects.

.. note::
    From the address in the uri that was printed you can see that Pyro by default binds its daemons on localhost.
    This means you cannot reach them from another machine on the network (a security measure).
    If you want to be able to talk to the daemon from other machines, you have to
    explicitly provide a hostname to bind on. This is done by giving a ``host`` argument to
    the daemon, see the paragraphs below for more details on this.

.. index:: private methods

.. note:: **Private methods:**
    Pyro considers any method or attribute whose name starts with at least one underscore ('_'), private.
    These cannot be accessed remotely.
    An exception is made for the 'dunder' methods with double underscores, such as ``__len__``. Pyro follows
    Python itself here and allows you to access these as normal methods, rather than treating them as private.

.. note::
    You can publish any regular Python object as a Pyro object.
    However since Pyro adds a few Pyro-specific attributes to the object, you can't use:

    * types that don't allow custom attributes, such as the builtin types (``str`` and ``int`` for instance)
    * types with ``__slots__`` (a possible way around this is to add Pyro's custom attributes to your ``__slots__``, but that isn't very nice)


.. index::
    instance modes; instance_mode
    instance modes; instance_creator
.. _server-instancemode:

Instance modes and Instance creation
------------------------------------

Instead of registering an *object* with the daemon, you can also register a *class* instead.
When doing that, it is Pyro itself that creates an instance (object).
This allows for more control over when and for how long Pyro creates objects.
It is also the preferred way of registering your code with the daemon.

Controlling the instance mode and creation is done via the ``instance_mode`` and ``instance_creator``
parameters of the ``expose`` decorator, which was described earlier.
By the way, it is *not* required to have ``REQUIRE_EXPOSE`` set to true to use these.
You can control the instance mode regardless of this setting because it only influences what methods
and attributes of the class are exposed.

By default, Pyro will create an instance of your class per *session* (=proxy connection)
Here is an example of registering a class that will have one new instance for every single method call instead::

    import Pyro4

    @Pyro4.expose(instance_mode="percall")
    class MyPyroThing(object):
        # ... methods that can be called go here...
        pass

    daemon = Pyro4.Daemon()
    uri = daemon.register(MyPyroThing)
    print(uri)
    daemon.requestLoop()

There are three possible choices for the ``instance_mode`` parameter:

- ``session``: (the default) a new instance is created for every new proxy connection, and is reused for
  all the calls during that particular proxy session. Other proxy sessions will deal with a different instance.
- ``single``: a single instance will be created and used for all method calls, regardless what proxy
  connection we're dealing with. This is the same as creating and registering a single object yourself
  (the old style of registering code with the deaemon). Be aware that the methods on this object can be called
  from separate threads concurrently.
- ``percall``: a new instance is created for every single method call, and discarded afterwards.


**Instance creation**

.. sidebar:: Instance creation is lazy

    When you register a class in this way, be aware that Pyro only creates an actual
    instance of it when it is first needed. If nobody connects to the deamon requesting
    the services of this class, no instance will ever be created.

Normally Pyro will simply use a default parameterless constructor call to create the instance.
If you need special initialization or the class's init method requires parameters, you have to specify
an ``instance_creator`` callable as well. Pyro will then use that to create an instance of your class.
It will call it with the class to create an instance of as the single parameter.

See the :file:`instancemode` example to learn about various ways to use this.
See the :file:`usersession` example to learn how you could use it to build user-bound resource access without concurrency problems.


.. index:: publishing objects oneliner, serveSimple
.. _server-servesimple:

Oneliner Pyro object publishing: serveSimple()
----------------------------------------------
Ok not really a one-liner, but one statement: use :py:meth:`serveSimple` to publish a dict of objects/classes and start Pyro's request loop.
The code above could also be written as::

    import Pyro4

    class MyPyroThing(object):
        pass

    obj = MyPyroThing()
    Pyro4.Daemon.serveSimple(
        {
            MyPyroThing: None,    # register the class
            obj: None             # register one specific instance
        },
        ns=False)

You can perform some limited customization:

.. py:staticmethod:: Daemon.serveSimple(objects [host=None, port=0, daemon=None, ns=True, verbose=True])

    Very basic method to fire up a daemon that hosts a bunch of objects.
    The objects will be registered automatically in the name server if you specify this.
    API reference: :py:func:`Pyro4.core.Daemon.serveSimple`

    :param objects: mapping of objects/classes to names, these are the Pyro objects that will be hosted by the daemon, using the names you provide as values in the mapping.
        Normally you'll provide a name yourself but in certain situations it may be useful to set it to ``None``. Read below for the exact behavior there.
    :type objects: dict
    :param host: optional hostname where the daemon should be accessible on. Necessary if you want to access the daemon from other machines.
    :type host: str or None
    :param port: optional port number where the daemon should be accessible on
    :type port: int
    :param daemon: optional existing daemon to use, that you created yourself.
        If you don't specify this, the method will create a new daemon object by itself.
    :type daemon: Pyro4.core.Daemon
    :param ns: optional, if True (the default), the objects will also be registered in the name server (located using :py:meth:`Pyro4.locateNS`) for you.
        If this parameters is False, your objects will only be hosted in the daemon and are not published in a name server.
        Read below about the exact behavior of the object names you provide in the ``objects`` dictionary.
    :type ns: bool
    :param verbose: optional, if True (the default), print out a bit of info on the objects that are registered
    :type verbose: bool
    :returns: nothing, it starts the daemon request loop and doesn't return until that stops.

If you set ``ns=True`` your objects will appear in the name server as well (this is the default setting).
Usually this means you provide a logical name for every object in the ``objects`` dictionary.
If you don't (= set it to ``None``), the object will still be available in the daemon (by a generated name) but will *not* be registered
in the name server (this is a bit strange, but hey, maybe you don't want all the objects to be visible in the name server).

When not using a name server at all (``ns=False``), the names you provide are used as the object names
in the daemon itself. If you set the name to ``None`` in this case, your object will get an automatically generated internal name,
otherwise your own name will be used.

.. important::
    - The names you provide for each object have to be unique (or ``None``). For obvious reasons you can't register multiple objects with the same names.
    - if you use ``None`` for the name, you have to use the ``verbose`` setting as well, otherwise you won't know the name that Pyro generated for you.
      That would make your object more or less unreachable.

The uri that is used to register your objects in the name server with, is ofcourse generated by the daemon.
So if you need to influence that, for instance because of NAT/firewall issues,
it is the daemon's configuration you should be looking at.

If you don't provide a daemon yourself, :py:meth:`serveSimple` will create a new one for you using the default configuration or
with a few custom parameters you can provide in the call, as described above.
If you don't specify the ``host`` and ``port`` parameters, it will simple create a Daemon using the default settings.
If you *do* specify ``host`` and/or ``port``, it will use these as parameters for creating the Daemon (see next paragraph).
If you need to further tweak the behavior of the daemon, you have to create one yourself first, with the desired
configuration. Then provide it to this function using the ``daemon`` parameter. Your daemon will then be used instead of a new one::

    custom_daemon = Pyro4.Daemon(host="example", nathost="example")    # some additional custom configuration
    Pyro4.Daemon.serveSimple(
        {
            MyPyroThing(): None
        },
        daemon = custom_daemon)


.. index::
    double: Pyro daemon; creating a daemon

Creating a Daemon
-----------------
Pyro's daemon is ``Pyro4.Daemon`` (shortcut to :class:`Pyro4.core.Daemon`).
It has a few optional arguments when you create it:


.. function:: Daemon([host=None, port=0, unixsocket=None, nathost=None, natport=None, interface=DaemonObject])

    Create a new Pyro daemon.

    :param host: the hostname or IP address to bind the server on. Default is ``None`` which means it uses the configured default (which is localhost).
                 It is necessary to set this argument to a visible hostname or ip address, if you want to access the daemon from other machines.
    :type host: str or None
    :param port: port to bind the server on. Defaults to 0, which means to pick a random port.
    :type port: int
    :param unixsocket: the name of a Unix domain socket to use instead of a TCP/IP socket. Default is ``None`` (don't use).
    :type unixsocket: str or None
    :param nathost: hostname to use in published addresses (useful when running behind a NAT firewall/router). Default is ``None`` which means to just use the normal host.
                    For more details about NAT, see :ref:`nat-router`.
    :type host: str or None
    :param natport: port to use in published addresses (useful when running behind a NAT firewall/router). If you use 0 here,
                    Pyro will replace the NAT-port by the internal port number to facilitate one-to-one NAT port mappings.
    :type port: int
    :param interface: optional alternative daemon object implementation (that provides the Pyro API of the daemon itself)
    :type interface: Pyro4.core.DaemonObject


.. index::
    double: Pyro daemon; registering objects/classes

Registering objects/classes
---------------------------
Every object you want to publish as a Pyro object needs to be registered with the daemon.
You can let Pyro choose a unique object id for you, or provide a more readable one yourself.

.. method:: Daemon.register(obj_or_class [, objectId=None, force=False])

    Registers an object with the daemon to turn it into a Pyro object.

    :param obj_or_class: the instance or class to register
    :param objectId: optional custom object id (must be unique). Default is to let Pyro create one for you.
    :type objectId: str or None
    :param force: optional flag to force registration, normally Pyro checks if an object had already been registered.
        If you set this to True, the previous registration (if present) will be silently overwritten.
    :type force: bool
    :returns: an uri for the object
    :rtype: :class:`Pyro4.core.URI`

It is important to do something with the uri that is returned: it is the key to access the Pyro object.
You can save it somewhere, or perhaps print it to the screen.
The point is, your client programs need it to be able to access your object (they need to create a proxy with it).

Maybe the easiest thing is to store it in the Pyro name server.
That way it is almost trivial for clients to obtain the proper uri and connect to your object.
See :doc:`nameserver` for more information (:ref:`nameserver-registering`), but it boils down to
getting a name server proxy and using its ``register`` method::

    uri = daemon.register(some_object)
    ns = Pyro4.locateNS()
    ns.register("example.objectname", uri)


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
    print("uri=",uri)
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
    print(thing.method(42))   # prints 84

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
    daemon = Pyro4.Daemon(host="yourhostname")
    ns = Pyro4.locateNS()
    uri = daemon.register(Thing())
    ns.register("mythingy", uri)
    daemon.requestLoop()

    # ------ alternatively, using serveSimple -----
    Pyro4.Daemon.serveSimple(
        {
            Thing(): "mythingy"
        },
        ns=True, verbose=True, host="yourhostname")

Client code example to connect to this object::

    import Pyro4
    thing = Pyro4.Proxy("PYRONAME:mythingy")
    print(thing.method(42))   # prints 84


.. index::
    double: Pyro daemon; unregistering objects

Unregistering objects
---------------------
When you no longer want to publish an object, you need to unregister it from the daemon:

.. method:: Daemon.unregister(objectOrId)

    :param objectOrId: the object to unregister
    :type objectOrId: object itself or its id string


.. index:: request loop

Running the request loop
------------------------
Once you've registered your Pyro object you'll need to run the daemon's request loop to make
Pyro wait for incoming requests.

.. method:: Daemon.requestLoop([loopCondition])

    :param loopCondition: optional callable returning a boolean, if it returns False the request loop will be aborted and the call returns

This is Pyro's event loop and it will take over your program until it returns (it might never.)
If this is not what you want, you can control it a tiny bit with the ``loopCondition``, or read the next paragraph.

.. index::
    double: event loop; integrate Pyro's requestLoop

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

.. index:: Combining Daemons

Combining Daemon request loops
------------------------------
In certain situations you will be dealing with more than one daemon at the same time.
For instance, when you want to run your own Daemon together with an 'embedded' Name Server Daemon,
or perhaps just another daemon with different settings.

Usually you run the daemon's :meth:`Pyro4.core.Daemon.requestLoop` method to handle incoming requests.
But when you have more than one daemon to deal with, you have to run the loops of all of them in parallel somehow.
There are a few ways to do this:

1. multithreading: run each daemon inside its own thread
2. multiplexing event loop: write a multiplexing event loop and call back into the appropriate
   daemon when one of its connections send a request.
   You can do this using :mod:`selectors` or :mod:`select` and you can even integrate other (non-Pyro)
   file-like selectables into such a loop. Also see the paragraph above.
3. use :meth:`Pyro4.core.Daemon.combine` to combine several daemons into one,
   so that you only have to call the requestLoop of that "master daemon".
   Basically Pyro will run an integrated multiplexed event loop for you.
   You can combine normal Daemon objects, the NameServerDaemon and also the name server's BroadcastServer.
   Again, have a look at the :file:`eventloop` example to see how this can be done.
   (Note: this will only work with the ``multiplex`` server type, not with the ``thread`` type)


.. index::
    double: Pyro daemon; shutdown
    double: Pyro daemon; cleaning up

Cleaning up
-----------
To clean up the daemon itself (release its resources) either use the daemon object
as a context manager in a ``with`` statement, or manually call :py:meth:`Pyro4.core.Daemon.close`.

Ofcourse, once the daemon is running, you first need a clean way to stop the request loop before
you can even begin to clean things up.

You can use force and hit ctrl-C or ctrl-\ or ctrl-Break to abort the request loop, but
this usually doesn't allow your program to clean up neatly as well.
It is therefore also possible to leave the loop cleanly from within your code (without using :py:meth:`sys.exit` or similar).
You'll have to provide a ``loopCondition`` that you set to ``False`` in your code when you want
the daemon to stop the loop. You could use some form of semi-global variable for this.
(But if you're using the threaded server type, you have to also set ``COMMTIMEOUT`` because otherwise
the daemon simply keeps blocking inside one of the worker threads).

Another possibility is calling  :py:meth:`Pyro4.core.Daemon.shutdown` on the running daemon object.
This will also break out of the request loop and allows your code to neatly clean up after itself,
and will also work on the threaded server type without any other requirements.

If you are using your own event loop mechanism you have to use something else, depending on your own loop.


.. index:: automatic proxying

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

Note that when using the marshal serializer, this feature doesn't work. You have to use
one of the other serializers to use autoproxying. Also, it doesn't work correctly when
you are using old-style classes (but they are from Python 2.2 and earlier, you should
not be using these anyway).


.. index:: concurrency model, server types, SERVERTYPE

.. _object_concurrency:

Server types and Concurrency model
==================================
Pyro supports multiple server types (the way the Daemon listens for requests). Select the
desired type by setting the ``SERVERTYPE`` config item. It depends very much on what you
are doing in your Pyro objects what server type is most suitable. For instance, if your Pyro
object does a lot of I/O, it may benefit from the parallelism provided by the thread pool server.
However if it is doing a lot of CPU intensive calculations, the multiplexed server may be more
appropriate. If in doubt, go with the default setting.

.. index::
    double: server type; threaded

1. threaded server (servertype ``"thread"``, this is the default)
    This server uses a thread pool to handle incoming proxy connections.
    The size of the pool is configurable via various config items.
    Every proxy on a client that connects to the daemon will be assigned to a thread to handle
    the remote method calls. This way multiple calls can potentially be processed concurrently.
    This means your Pyro object may have to be made *thread-safe*!
    If you registered the pyro object's class with instance mode ``single``, that single instance
    will be called concurrently from different threads. If you used instance mode ``session`` or ``percall``,
    the instance will not be called from different threads because a new one is made per connection or even per call.
    But in every case, if you access a shared resource from your Pyro object,
    you may need to take thread locking measures such as using Queues.
    If the thread pool is too small for the number of proxy connections, new proxy connections will
    be put to wait until another proxy disconnects from the server.

.. index::
    double: server type; multiplex

2. multiplexed server (servertype ``"multiplex"``)
    This server uses a connection multiplexer to process
    all remote method calls sequentially. No threads are used in this server.
    It uses the best supported selector available on your platform (kqueue, poll, select).
    It means only one method call is running at a time, so if it takes a while to complete, all other
    calls are waiting for their turn (even when they are from different proxies).
    The instance mode used for registering your class, won't change the way
    the concurrent access to the instance is done: in all cases, there is only one call active at all times.
    Your objects will never be called concurrently from different threads, because there are no threads.
    It does still affect when and how often Pyro creates an instance of your class.

.. note::
    If the ``ONEWAY_THREADED`` config item is enabled (it is by default), *oneway* method calls will
    be executed in a separate worker thread, regardless of the server type you're using.

.. index::
    double: server type; what to choose?

*When to choose which server type?*
With the threadpool server at least you have a chance to achieve concurrency, and
you don't have to worry much about blocking I/O in your remote calls. The usual
trouble with using threads in Python still applies though:
Python threads don't run concurrently unless they release the :abbr:`GIL (Global Interpreter Lock)`.
If they don't, you will still hang your server process.
For instance if a particular piece of your code doesn't release the :abbr:`GIL (Global Interpreter Lock)` during
a longer computation, the other threads will remain asleep waiting to acquire the :abbr:`GIL (Global Interpreter Lock)`. One of these threads may be
the Pyro server loop and then your whole Pyro server will become unresponsive.
Doing I/O usually means the :abbr:`GIL (Global Interpreter Lock)` is released.
Some C extension modules also release it when doing their work. So, depending on your situation, not all hope is lost.

With the multiplexed server you don't have threading problems: everything runs in a single main thread.
This means your requests are processed sequentially, but it's easier to make the Pyro server
unresponsive. Any operation that uses blocking I/O or a long-running computation will block
all remote calls until it has completed.

.. index::
    double: server; serialization

Serialization
=============
Pyro will serialize the objects that you pass to the remote methods, so they can be sent across
a network connection. Depending on the serializer that is being used for your Pyro server,
there will be some limitations on what objects you can use, and what serialization format is
required of the clients that connect to your server.

You specify one or more serializers that are accepted in the daemon/server by setting the
``SERIALIZERS_ACCEPTED`` config item. This is a set of serializer names
that are allowed to be used with your server.  It defaults to the set of 'safe' serializers.
A client that successfully talks to your server will get responses using the same
serializer as the one used to send requests to the server.

If your server also uses Pyro client code/proxies, you might also need to
select the serializer for these by setting the ``SERIALIZER`` config item.

See the :doc:`/config` chapter for details about the config items.
See :ref:`object-serialization` for more details about serialization, the new config items,
and how to deal with existing code that relies on pickle.

.. note::
    Since Pyro 4.20 the default serializer is "``serpent``". It used to be "``pickle``" in older versions.
    The default set of accepted serializers in the server is the set of 'safe' serializers,
    so "``pickle``" and "``dill``" are not among the default.


Other features
==============

.. index:: attributes added to Pyro objects

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

.. index:: network adapter binding, IP address, localhost, 127.0.0.1

Network adapter binding and localhost
-------------------------------------

All Pyro daemons bind on localhost by default. This is because of security reasons.
This means only processes on the same machine have access to your Pyro objects.
If you want to make them available for remote machines, you'll have to tell Pyro on what
network interface address it must bind the daemon.
This also extends to the built in servers such as the name server.

.. warning::
    Read chapter :doc:`security` before exposing Pyro objects to remote machines!

There are a few ways to tell Pyro what network address it needs to use.
You can set a global config item ``HOST``, or pass a ``host`` parameter to the constructor of a Daemon,
or use a command line argument if you're dealing with the name server.
For more details, refer to the chapters in this manual about the relevant Pyro components.

Pyro provides a couple of utility functions to help you with finding the appropriate IP address
to bind your servers on if you want to make them publicly accessible:

* :py:func:`Pyro4.socketutil.getIpAddress`
* :py:func:`Pyro4.socketutil.getInterfaceAddress`


Cleaning up / disconnecting stale client connections
----------------------------------------------------
A client proxy will keep a connection open even if it is rarely used.
It's good practice for the clients to take this in consideration and release the proxy.
But the server can't enforce this, some clients may keep a connection open for a long time.
Unfortunately it's hard to tell when a client connection has become stale (unused).
Pyro's default behavior is to accept this fact and not kill the connection.
This does mean however that many stale client connections will eventually block the
server's resources, for instance all workers threads in the threadpool server.

There's a simple possible solution to this, which is to specify a communication timeout
on your server. For more information about this, read :ref:`tipstricks_release_proxy`.


.. index:: Daemon API

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

