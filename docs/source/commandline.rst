.. _command-line:

Command line tools
******************

Pyro has several command line tools that you will be using sooner or later.

For now, there are no special scripts or executables that call those tools directly.
Instead, they're "executable modules" inside Pyro. They're invoked with Python's "-m"
command line argument.

An idea is to define shell aliases for them, for instance:
:kbd:`alias pyrons='python -m Pyro4.naming'`

.. _command-line-nameserver:

Name server
===========
synopsys: :command:`python -m Pyro4.naming [options]`

Starts the Pyro Name Server. It can run without any arguments but there are several that you
can use, for instance to control the hostname and port that the server is listening on.
A short explanation of the available options can be printed with the help option:

.. program:: Pyro4.naming

.. option:: -h, --help

   Print a short help message and exit.

Detailed information is available here: :ref:`name-server`.

Name server control
===================
:command:`python -m Pyro4.nsc [options] command [arguments]`

The name server control tool (or 'nsc') is used to talk to a running name server and perform
diagnostic or maintenance actions such as querying the registered objects, adding or removing
a name registration manually, etc.
A short explanation of the available options can be printed with the help option:

.. program:: Pyro4.nsc

.. option:: -h, --help

   Print a short help message and exit.

The available commands are:

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
