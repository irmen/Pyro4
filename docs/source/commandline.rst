.. _command-line:

******************
Command line tools
******************

Pyro has several command line tools that you will be using sooner or later.

For now, there are no special scripts or executables that call those tools directly.
Instead, they're "executable modules" inside Pyro. They're invoked with Python's "-m"
command line argument.

An idea is to define shell aliases for them, for instance:
:kbd:`alias pyrons='python -m Pyro4.naming'`


Name server
===========
synopsys: :command:`python -m Pyro4.naming [options]`

Starts the Pyro Name Server. It can run without any arguments but there are several that you
can use, for instance to control the hostname and port that the server is listening on.
A short explanation of the available options can be printed with the help option:

.. program:: Pyro4.naming

.. option:: -h, --help

   Print a short help message and exit.

.. seealso:: :ref:`nameserver-nameserver` for detailed information

Name server control
===================
synopsys: :command:`python -m Pyro4.nsc [options] command [arguments]`

The name server control tool (or 'nsc') is used to talk to a running name server and perform
diagnostic or maintenance actions such as querying the registered objects, adding or removing
a name registration manually, etc.
A short explanation of the available options can be printed with the help option:

.. program:: Pyro4.nsc

.. option:: -h, --help

   Print a short help message and exit.

.. seealso:: :ref:`nameserver-nsc` for detailed information


.. _command-line-echoserver:

Test echo server
================
:command:`python -m Pyro4.test.echoserver [options]`

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


Configuration check
===================
:command:`python -m Pyro4.configuration`
This is the equivalent of::

  >>> import Pyro4
  >>> print Pyro4.config.dump()

It prints the Pyro version, the location it is imported from, and a dump of the active configuration items.
