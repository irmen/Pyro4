***************************
Servers: publishing objects
***************************

This chapter explains how you write code that publishes objects to be remotely accessible.
These objects are then called *Pyro objects* and the program that provides them,
is often called a *server* program.

(The program that calls the objects is usually called the *client*.
Both roles can be mixed in a single program.)

Make sure you are familiar with Pyro's :ref:`keyconcepts` before reading on.

.. note::
    See :doc:`config` for several config items that you can use to tweak various server side aspects.


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

Note that the amount of options you can provide is very limited.
If you want to control the way the Pyro daemon is constructed (for instance, to make
it listen on a different ip address than localhost), you'll have to do that by setting
the appropriate config options before calling ``serveSimple``.
Or you can create a daemon object yourself with the right arguments,
and pass that to ``serveSimple`` so that it doesn't create a default daemon itself.

Creating a Daemon
-----------------
Pyro's daemon is :class:`Pyro4.core.Daemon` and you can also access it by its shortcut ``Pyro4.Daemon``.
It has a few optional arguments when you create it:


.. function:: Daemon([host=None][, port=0][, unixsocket=None])

    Create a new Pyro daemon.

    :param host: the hostname or IP address to bind the server on. Default is ``None`` which means it uses the configured default (which is localhost).
    :type host: str or None
    :param port: port to bind the server on. Defaults to 0, which means to pick a random port.
    :type port: int
    :param unixsocket: the name of a unix domain socket to use instead of a TCP/IP socket. Default is ``None`` (don't use).
    :type unixsocket: str or None


Registering objects
-------------------
Every object you want to publish as a Pyro object needs to be registered with the daemon.
You can let Pyro choose a unique object id for you, or provide a more readable one yourself.

.. method:: Daemon.register(obj[, objectId=None])

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

Server types and Object concurrency model (@todo)
=================================================
@todo
threaded server
multiplexed server


Other features (@todo)
======================

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

Network adapter binding (@todo)
-------------------------------
@todo Default: localhost. See :doc:`security`.

Daemon Pyro interface (@todo)
-----------------------------
@todo see :class:`Pyro4.core.DaemonObject`
