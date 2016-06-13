.. index:: FLAME

************************************************
Flame: Foreign Location Automatic Module Exposer
************************************************

.. image:: _static/flammable.png
       :align: left

Pyro Flame is an easy way of exposing remote modules and builtins, and even a remote interactive
Python console. It is available since Pyro 4.10.
With Flame, you don't need to write any server side code anymore, and still be
able to call objects, modules and other things on the remote machine.
Flame does this by giving a client direct access to any module or builtin that is available on the remote machine.

Flame can be found in the :py:mod:`Pyro4.utils.flame` module.

.. warning:: Be very sure about what you are doing before enabling Flame.

    Flame is disabled by default. You need to explicitly set a config item
    to true, and start a Flame server yourself, to make it available.
    This is because it allows client programs full access to *everything* on your system.
    Only use it if you fully trust your environment and the clients that can connect to your machines.

    (Flame is also symbolic for burning server machines that got totally owned by malicious clients.)


.. index:: enabling Flame

Enabling Flame
==============
Flame is actually a special Pyro object that is exposed via a normal Pyro daemon.
You need to start it explicitly in your daemon. This is done by calling a utility
function with your daemon that you want to enable flame on::

    import Pyro4.utils.flame
    Pyro4.utils.flame.start(daemon)

Additionally, you have to make some configuration changes:

* flame server: set the ``FLAME_ENABLED`` config item to True
* flame server: set the ``SERIALIZERS_ACCEPTED`` config item to ``{"pickle"}``
* flame client: set the ``SERIALIZER`` config item to ``pickle``

You'll have to explicitly enable Flame. When you don't, you'll
get an error when trying to start Flame. The config item is False by default
to avoid unintentionally running Flame servers.
Also, Flame requires the pickle serializer. It doesn't work when using one of
the secure serializers, because it needs to be able to transfer custom python objects.


.. index::
    double: command line; Flame server

Command line server
===================
There's a little command line server program that will launch a flame enabled Pyro daemon,
to avoid the hassle of having to write a custom server program yourself everywhere you want
to provide a Flame server:

:command:`python -m Pyro4.utils.flameserver` (or simply: :command:`pyro4-flameserver`)

The command line arguments are similar to the echo server (see :ref:`command-line-echoserver`).
Use ``-h`` to make it print a short help text. For the command line server you'll also have
to set the ``FLAME_ENABLED`` config item to True, otherwise you'll get an error when trying to start it.
Because we're talking about command line clients, the most convenient way to do so is probably by
setting the environment variable in your shell: ``PYRO_FLAME_ENABLED=true``.


.. index:: Flame object

Flame object and examples
=========================
A Flame server exposes a ``"Pyro.Flame"`` object (you can hardcode this name or use the
constant :py:attr:`Pyro4.constants.FLAME_NAME`).
Its interface is described in the API documentation, see :py:class:`Pyro4.utils.flame.Flame`.

Connecting to the flame server can be done as usual (by creating a Pyro proxy yourself)
or by using the convenience function :py:func:`Pyro4.utils.flame.connect`.
A little example follows. You have to have running flame server, and then you can write a client like this::

    import Pyro4.utils.flame

    Pyro4.config.SERIALIZER = "pickle"    # flame requires pickle serializer

    flame = Pyro4.utils.flame.connect("hostname:9999")    # or whatever the server runs at

    socketmodule = flame.module("socket")
    osmodule = flame.module("os")
    print("remote host name=", socketmodule.gethostname())
    print("remote server directory contents=", osmodule.listdir("."))

    flame.execute("import math")
    root = flame.evaluate("math.sqrt(500)")
    print("calculated square root=", root)
    print("remote exceptions also work", flame.evaluate("1//0"))

    # print something on the remote std output
    flame.builtin("print")("Hello there, remote server stdout!")


.. index:: Flame remote console

A remote interactive console can be started like this::

    with flame.console() as console:
        console.interact()
        # ... you can repeat sessions if you want

... which will print something like::

    Python 2.7.2 (default, Jun 12 2011, 20:46:48)
    [GCC 4.2.1 (Apple Inc. build 5577)] on darwin
    (Remote console on charon:9999)
    >>> # type stuff here and it gets executed on the remote machine
    >>> import socket
    >>> socket.gethostname()
    'charon.local'
    >>> ^D
    (Remote session ended)


.. index:: getfile, sendfile

.. note::
    The ``getfile`` and ``sendfile`` functions can be used for *very* basic file transfer.

    The ``getmodule`` and ``sendmodule`` functions can be used to send module source files
    to other machines so it is possible to execute code that wasn't available before.
    This is a *very* experimental replacement of the mobile code feature that Pyro 3.x had.
    It also is a very easy way of totally owning the server because you can make it execute
    anything you like. Be very careful.

.. note::

    :doc:`pyrolite` also supports convenient access to a Pyro Flame server. This includes the remote interactive console.


See the :file:`flame` example for example code including uploading module source code to the server.
