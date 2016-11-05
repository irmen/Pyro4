.. index:: configuration

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

.. index::
    double: configuration; environment variables

You can also set them outside of your program, using environment variables from the shell.
**To avoid conflicts, the environment variables have a ``PYRO_`` prefix.** This means that if you want
to change the same two settings as above, but by using environment variables, you would do something like::

    $ export PYRO_COMPRESSION=true
    $ export PYRO_SERVERTYPE=multiplex

    (or on windows:)
    C:\> set PYRO_COMPRESSION=true
    C:\> set PYRO_SERVERTYPE=multiplex

This environment defined configuration is simply used as initial values for Pyro's configuration object.
Your code can still overwrite them by setting the items to other values, or by resetting the config as a whole.


.. index:: reset config to default

Resetting the config to default values
--------------------------------------

.. method:: Pyro4.config.reset([useenvironment=True])

    Resets the configuration items to their builtin default values.
    If `useenvironment` is True, it will overwrite builtin config items with any values set
    by environment variables. If you don't trust your environment, it may be a good idea
    to reset the config items to just the builtin defaults (ignoring any environment variables)
    by calling this method with `useenvironment` set to False.
    Do this before using any other part of the Pyro library.


.. index:: current config, pyro4-check-config

Inspecting current config
-------------------------

To inspect the current configuration you have several options:

1. Access individual config items: ``print(Pyro4.config.COMPRESSION)``
2. Dump the config in a console window: :command:`python -m Pyro4.configuration` (or simply :command:`pyro4-check-config`)
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


.. index:: configuration items

.. _config-items:

Overview of Config Items
------------------------

======================= ======= ============== =======
config item             type    default        meaning
======================= ======= ============== =======
AUTOPROXY               bool    True           Enable to make Pyro automatically replace Pyro objects by proxies in the method arguments and return values of remote method calls. Doesn't work with marshal serializer.
COMMTIMEOUT             float   0.0            network communication timeout in seconds. 0.0=no timeout (infinite wait)
COMPRESSION             bool    False          Enable to make Pyro compress the data that travels over the network
DETAILED_TRACEBACK      bool    False          Enable to get detailed exception tracebacks (including the value of local variables per stack frame)
HOST                    str     localhost      Hostname where Pyro daemons will bind on
MAX_MESSAGE_SIZE        int     0              Maximum size in bytes of the messages sent or received on the wire. If a message exceeds this size, a ProtocolError is raised.
NS_HOST                 str     *equal to      Hostname for the name server. Used for locating in clients only (use the normal HOST config item in the name server itself)
                                HOST*
NS_PORT                 int     9090           TCP port of the name server. Used by the server and for locating in clients.
NS_BCPORT               int     9091           UDP port of the broadcast responder from the name server. Used by the server and for locating in clients.
NS_BCHOST               str     None           Hostname for the broadcast responder of the name sever. Used by the server only.
NS_AUTOCLEAN            float   0.0            Specify a recurring period in seconds where the Name server checks its registrations and removes the ones that are not available anymore. (0=disabled, otherwise should be >=3)
NATHOST                 str     None           External hostname in case of NAT (used by the server)
NATPORT                 int     None           External port in case of NAT (used by the server)
BROADCAST_ADDRS         str     <broadcast>,   List of comma separated addresses that Pyro should send broadcasts to (for NS locating in clients)
                                0.0.0.0
ONEWAY_THREADED         bool    True           Enable to make oneway calls be processed in their own separate thread
POLLTIMEOUT             float   2.0            For the multiplexing server only: the timeout of the select or poll calls
SERVERTYPE              str     thread         Select the Pyro server type. thread=thread pool based, multiplex=select/poll/kqueue based
SOCK_REUSE              bool    False          Should SO_REUSEADDR be used on sockets that Pyro creates.
PREFER_IP_VERSION       int     4              The IP address type that is preferred (4=ipv4, 6=ipv6, 0=let OS decide).
THREADING2              bool    False          Use the threading2 module if available instead of Python's standard threading module
THREADPOOL_SIZE         int     40             For the thread pool server: maximum number of threads running
THREADPOOL_SIZE_MIN     int     4              For the thread pool server: minimum number of threads running
FLAME_ENABLED           bool    False          Should Pyro Flame be enabled on the server
SERIALIZER              str     serpent        The wire protocol serializer to use for clients/proxies (one of: serpent, json, marshal, pickle, dill)
SERIALIZERS_ACCEPTED    set     json,marshal,  The wire protocol serializers accepted in the server/daemon. In your code it should be a set of strings,
                                serpent        use a comma separated string instead when setting the shell environment variable.
PICKLE_PROTOCOL_VERSION int     highest poss   The pickle protocol version to use, if pickle is selected as serializer. Defaults to pickle.HIGHEST_PROTOCOL
DILL_PROTOCOL_VERSION   int     highest poss   The dill protocol version to use, if dill is selected as serializer. Defaults to `-1` (highest protocol).
JSON_MODULE             string  json           The json module to use for the json serializer. (json is included in the stdlib, simplejson is a possible 3rd party alternative).
LOGWIRE                 bool    False          If wire-level message data should be written to the logfile (you may want to disable COMPRESSION)
METADATA                bool    True           Client: Get remote object metadata from server automatically on proxy connect (methods, attributes, oneways, etc) and use local checks in the proxy against it (set to False to use compatible behavior with Pyro 4.26 and earlier)
REQUIRE_EXPOSE          bool    True           Server: Is @expose required to make members remotely accessible. If False, everything is accessible (use this only for backwards compatibility).
USE_MSG_WAITALL         bool    True (False if Some systems have broken socket MSG_WAITALL support. Set this item to False if your system is one of these. Pyro will then use another (but slower) piece of code to receive network data.
                                on Windows)
MAX_RETRIES             int     0              Automatically retry network operations for some exceptions (timeout / connection closed), be careful to use when remote functions have a side effect (e.g.: calling twice results in error)
ITER_STREAMING          bool    True           Should iterator item streaming support be enabled in the server (default=True)
ITER_STREAM_LIFETIME    float   0.0            Maximum lifetime in seconds for item streams (default=0, no limit - iterator only stops when exhausted or client disconnects)
ITER_STREAM_LINGER      float   30.0           Linger time in seconds to keep an item stream alive after proxy disconnects (allows to reconnect to stream)
======================= ======= ============== =======

.. index::
    double: configuration items; logging

There are two special config items that control Pyro's logging, and that are only available as environment variable settings.
This is because they are used at the moment the Pyro4 package is being imported
(which means that modifying them as regular config items after importing Pyro4 is too late and won't work).

It is up to you to set the environment variable you want to the desired value. You can do this from your OS or shell,
or perhaps by modifying ``os.environ`` in your Python code *before* importing Pyro4.


======================= ======= ============== =======
environment variable    type    default        meaning
======================= ======= ============== =======
PYRO_LOGLEVEL           string  *not set*      The log level to use for Pyro's logger (DEBUG, WARN, ...) See Python's standard :py:mod:`logging` module for the allowed values (https://docs.python.org/2/library/logging.html#levels). If it is not set, no logging is being configured.
PYRO_LOGFILE            string  pyro.log       The name of the log file. Use {stderr} to make the log go to the standard error output.
======================= ======= ============== =======
