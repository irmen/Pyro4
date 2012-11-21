****************
Configuring Pyro
****************

Pyro can be configured using several *configuration items*.
The current configuration is accessible from the ``Pyro4.config`` object, it contains all config items as attributes.
You can read them and update them to change Pyro's configuration.
(usually you need to do this at the start of your program).
For instance, to enable message compression and change the server type, you add something like this to the start of your code::

  Pyro4.config.COMPRESSION = True
  Pyro4.config.SERVERTYPE = "multiplex"

You can also set them outside of your program, using environment variables from the shell.
To avoid conflicts, the environment variables have a ``PYRO_`` prefix. This means that if you want
to change the same two settings as above, but by using environment variables, you would do something like::

    $ export PYRO_COMPRESSION=true
    $ export PYRO_SERVERTYPE=multiplex

    (or on windows:)
    C:\> set PYRO_COMPRESSION=true
    C:\> set PYRO_SERVERTYPE=multiplex


Resetting the config to default values
--------------------------------------

.. method:: Pyro4.config.reset([useenvironment=True])

    Resets the configuration items to their builtin default values.
    If `useenvironment` is True, it will overwrite builtin config items with any values set
    by environment variables. If you don't trust your environment, it may be a good idea
    to reset the config items to just the builtin defaults (ignoring any environment variables)
    by calling this method with `useenvironment` set to False.
    Do this before using any other part of the Pyro library.


Inspecting current config
-------------------------

To inspect the current configuration you have several options:

1. Access individual config items: ``print(Pyro4.config.COMPRESSION)``
2. Dump the config in a console window: :command:`python -m Pyro4.configuration`
   This will print something like::

        Pyro version: 4.6
        Loaded from: E:\Projects\Pyro4\src\Pyro4
        Active configuration settings:
        AUTOPROXY = True
        COMMTIMEOUT = 0.0
        COMPRESSION = False
        ...

3. Access the config as a dictionary: ``Pyro4.config.asDict()``
4. Access the config string dump (used in #2): ``Pyro4.config.dump()``

.. _config-items:

Overview of Config Items
------------------------

======================= ======= ============== =======
config item             type    default        meaning
======================= ======= ============== =======
AUTOPROXY               bool    True           Enable to make Pyro automatically replace Pyro objects by proxies in the method arguments and return values of remote method calls
COMMTIMEOUT             float   0.0            network communication timeout in seconds. 0.0=no timeout (infinite wait)
COMPRESSION             bool    False          Enable to make Pyro compress the data that travels over the network
DETAILED_TRACEBACK      bool    False          Enable to get detailed exception tracebacks (including the value of local variables per stack frame)
DOTTEDNAMES             bool    False          Server side only: Enable to support object traversal using dotted names (a.b.c.d)
HMAC_KEY                bytes   None           Shared secret key to sign all communication messages
HOST                    str     localhost      Hostname where Pyro daemons will bind on
NS_HOST                 str     *equal to      Hostname for the name server
                                HOST*
NS_PORT                 int     9090           TCP port of the name server
NS_BCPORT               int     9091           UDP port of the broadcast responder from the name server
NS_BCHOST               str     None           Hostname for the broadcast responder of the name sever
NATHOST                 str     None           External hostname in case of NAT
NATPORT                 int     None           External port in case of NAT
BROADCAST_ADDRS         str     <broadcast>,   List of comma separated addresses that Pyro should send broadcasts to (for NS lookup)
                                0.0.0.0
ONEWAY_THREADED         bool    True           Enable to make oneway calls be processed in their own separate thread
POLLTIMEOUT             float   2.0            For the multiplexing server only: the timeout of the select or poll calls
SERVERTYPE              str     thread         Select the Pyro server type. thread=thread pool based, multiplex=select/poll based
SOCK_REUSE              bool    False          Should SO_REUSEADDR be used on sockets that Pyro creates.
THREADING2              bool    False          Use the threading2 module if available instead of Python's standard threading module
THREADPOOL_MINTHREADS   int     4              For the thread pool server: minimum amount of worker threads to be spawned
THREADPOOL_MAXTHREADS   int     50             For the thread pool server: maximum amount of worker threads to be spawned
THREADPOOL_IDLETIMEOUT  float   5.0            For the thread pool server: number of seconds to pass for an idle worker thread to be terminated
======================= ======= ============== =======

There are two special config items that are only available as environment variable settings.
This is because they are used at module import time (when the Pyro4 package is being imported).
They control Pyro's logging behavior:

======================= ======= ============== =======
environment variable    type    default        meaning
======================= ======= ============== =======
PYRO_LOGLEVEL           string  *not set*      The log level to use for Pyro's logger (DEBUG, WARN, ...) See Python's standard :py:mod:`logging` module for the allowed values. If it is not set, no logging is being configured.
PYRO_LOGFILE            string  pyro.log       The name of the log file. Use {stderr} to make the log go to the standard error output.
======================= ======= ============== =======
