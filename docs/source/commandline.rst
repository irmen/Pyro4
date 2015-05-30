.. index:: command line tools

.. _command-line:

******************
Command line tools
******************

Pyro has several command line tools that you will be using sooner or later. They are
generated and installed when you install Pyro.

- :command:`pyro4-ns` (name server)
- :command:`pyro4-nsc` (name server client tool)
- :command:`pyro4-test-echoserver` (test echo server)
- :command:`pyro4-check-config` (prints configuration)
- :command:`pyro4-flameserver` (flame server)
- :command:`pyro4-httpgateway` (http gateway server)

If you prefer, you can also invoke the various "executable modules" inside Pyro directly,
by using Python's "-m" command line argument.

Some of these tools are described in detail in their respective sections of the manual:

Name server tools:
    See :ref:`nameserver-nameserver` and :ref:`nameserver-nsc` for detailed information.

HTTP gateway server:
    See :ref:`http-gateway` for detailed information.


.. index::
    double: echo server; command line

.. _command-line-echoserver:

Test echo server
================
:command:`python -m Pyro4.test.echoserver [options]`  (or simply: :command:`pyro4-test-echoserver [options]`)

This is a simple built-in server that can be used for testing purposes.
It launches a Pyro object that has several methods suitable for various tests (see below).
Optionally it can also directly launch a name server. This way you can get a simple
Pyro server plus name server up with just a few keystrokes.

A short explanation of the available options can be printed with the help option:

.. program:: Pyro4.test.echoserver

.. option:: -h, --help

   Print a short help message and exit.

The echo server object is available by the name ``test.echoserver``. It exposes the following methods:

.. method:: echo(argument)

  Simply returns the given argument object again.

.. method:: error()

  Generates a run time exception.

.. method:: shutdown()

  Terminates the echo server.

.. index::
    double: configuration check; command line

Configuration check
===================
:command:`python -m Pyro4.configuration`  (or simply: :command:`pyro4-check-config`)
This is the equivalent of::

  >>> import Pyro4
  >>> print(Pyro4.config.dump())

It prints the Pyro version, the location it is imported from, and a dump of the active configuration items.
