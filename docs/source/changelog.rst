**********
Change Log
**********

**Pyro 4.35**

- removed Jython compatibility support and kludges. Use 4.34 or older if you need to run this in Jython.
- httpgateway is more forgiving when a name server is not (yet) found
- httpgateway now returns 403 forbidden instead of 401 unauthorized when accessing a resource without proper rights
- httpgateway gained -g option to set a key to use to access the gateway (like the hmac key to access pyro). Set $key querystring param to specify the key for a request.
- added X-Pyro-Gateway-Key http header to the httpgateway request as an alternative way to set the gateway key for the call
- serpent library dependency updated to 1.9, this adds support for serializing the container datatypes from the collections stdlib module
- introduced Pyro4.errors.SerializeError (subclass of ProtocolError) to be more precise in reporting errors related to (de)serializing objects.
- client gets a proper serialization error instead of getting a forced connection abort, if something goes wrong in a serializer.


**Pyro 4.34**

- NOTE: intending to drop support for Python 2.6 and Jython.
  This will probably be the last version that officially supports Python version 2.6 and Jython 2.7.
  Future versions will only be compatible with and tested with Python 2.7 and 3.2+, IronPython, and Pypy.
  The explicit Jython compatibility will be dropped. Until Jython 2.7 itself becomes up to par with official Python 2.7 you will probably no longer
  be able to use Pyro from within Jython. PyroLite will ofcourse still be supported for Java clients.
  If you're stuck with Python 2.6 (or Jython), plan on either committing to this last Pyro version that supports it, or plan on cloning the Pyro4
  source repository and applying compatibility patches yourself.
  This decision is made to remove the development and support burden that now exists for these old or problematic Python implementations.
- setting an attribute on a proxy as first operation no longer crashes with an AttributeError, it now correctly obtains the metadata first
- added JSON_MODULE config item to be able to set a 3rd party json library (such as simplejson) to use instead of the default json that comes in the stdlib.
- added X-Pyro-Options http header to the httpgateway request to set certain Pyro options for the call (such as 'oneway')
- http gateway name prefix option changed, you now specify an export name regex pattern instead (allows you to export multiple name patterns)
- http gateway gained a pyro timeout option as shortcut for Pyro's commtimeout config item that should be used
- fixed http example code when handling oneway methods (empty response)
- the nameserver's list function no longer internally appends a '$' (end of string marker) to a given regex pattern
- removed paragraph in docs about choosing between pyro4 and pyro3 (there's only one sensible choice nowadays)


**Pyro 4.33**

- added Pyro4.utils.httpgateway, this allows clients (such as a web browser) to use a simple http interface to call Pyro objects
- test.echoserver now correctly deals with a specified hmac key in combination with name server usage
- added connection troubleshooting checklist to tips & tricks chapter
- some raised exceptions had a __cause__ added on Python 2.x as well, this has been corrected (it could cause unwanted serialization errors)
- added http example that shows simple use of the http gateway
- fixed sphinx config issues when building the docs


**Pyro 4.32**

- json serializer can now deal with set() types; they will be converted to tuples/lists instead. (similar to what serpent does on older Python versions)
- this also fixes the problem that the proxy metadata feature used to crash when using json as serializer (because it used sets to transfer the data.
  You had to turn the metadata feature off to be able to use the json serializer at all)
- flame explicitly checks for pickle to be enabled instead of causing connection level errors
- PYRONAME uri resolving now also uses the _pyroHmacKey set on the proxy (if any)
- proxy no longer locks up in pyroRelease when a protocol error occurs while getting the metadata
- stockquotes tutorial doesn't actually require pickle anymore, so removed that from code and docs
- distributed-computing example now uses a custom class deserializer instead of relying on pickle
- distributed-computing example no longer overflows on older python versions (<3.x)
- serpent library dependency updated to 1.8
- setup.py no longer fails when it can't import Pyro4 (it no longer needs to do so)


**Pyro 4.31**

- locateNS now properly sets provided hmac key on proxy returned via broadcast lookup
- terminate call added to flame remoteconsole


**Pyro 4.30**

- Persistent name server option: -s (currently implemented: dbm, sqlite, and the default volatile in-memory storage)
- Name server utility methods have new 'storage' parameter to customize storage mechanism
- nsc got new 'lookup' command to get one single registration from the nameserver
- removed ``HMAC_KEY`` config item (deprecated in 4.29), use the ``_pyroHmacKey`` property on proxy and daemon instead.
  This finalizes the change that allows you to have a per-proxy hmac key instead of a single global one. (Also counts for daemons)
- name server and nsc command line tools gained -k/--key option to specify hmac key (just as the echoserver and flameserver already had)
- name server locateNS and resolve methods gained hmac key parameter
- configuration dump now also includes protocol version
- message class now has a static convenience 'ping' method to send ping messages. Useful for instance in the 'disconnects' example.


**Pyro 4.29**

- ``HMAC_KEY`` config item is deprecated, will be removed in next version
- set hmac key directly on ``proxy._pyroHmacKey`` property, this makes per-proxy hmac keys possible
- removed support for server side object traversal using dotted names such as a.b.c.d (has been deprecated since 4.27)
- removed ``DOTTEDNAMES`` config item (has been deprecated since 4.27)
- removed support for setting ``proxy._pyroOneway()`` in client code (has been deprecated since 4.27. You must depend on the metadata mechanism now, which is enabled by default)
- Future and FutureResult then() methods now return itself, so they can be easiliy chained
- added Future.iferror and FutureResult.iferror to handle exceptions (instead of silently ignoring them)
- fixed FutureResult.then to correctly evaluate all chained functions


**Pyro 4.28**

- implemented dir() on a Proxy to also return remote methods if known (useful for autocompletion in certain python shells)
- ``USE_MSG_WAITALL`` config item added because there remain certain other systems where ``MSG_WAITALL`` is unreliable
- removed ``Pyro4.socketutil.USE_MSG_WAITALL`` attribute (because it got promoted to a config item)
- remote access to 'dunder' attributes (``__whatever__``) is allowed again (pyro now follows python in making an exception for them rather than treating them as private)


**Pyro 4.27**

- requires serpent 1.7 or newer (because of some changes regarding to set literals and the error for circular references)
- added @Pyro4.expose and @Pyro4.oneway decorators
- attr lookup now actually honors 'private' attributes in all cases (name starting with underscore-- these are blocked from remote access no matter what)
- added METADATA config item to enable/disable the automatic metadata query that a proxy now does. To talk to older Pyro versions you'll have to set this to False.
- proper client side attribute validation if metadata is enabled. This also means that hasattr(proxy, "something") now actually works.
- added REQUIRE_EXPOSE config item to toggle exposing everything in a server object, or that you must cherrypick with the new @expose decorator
- copying a proxy now also copies its meta attributes (timeout, oneways, etc) instead of just the uri
- Proxy._pyroGetMetadata method added. Is used internally as well (if METADATA is enabled), to obtain info about remote object attributes and methods.
- The daemon got a new method that is used by the metadata mechanism: get_metadata
- Daemon can now be constructed with custom interface class (so you can change the behavior of the DaemonObject default implementation easily)
- echoserver gained a few more methods to test the new decorators
- DOTTEDNAMES is deprecated and will be removed in the next version
- setting proxy._pyroOneway yourself is deprecated and support for that will be removed in the next version
- locateNS() has a new parameter 'broadcast' to choose if it should use a broadcast lookup (default=True)
- the 'robots' example no longer requires pickle
- fixed the way the tracebacks are handled with the @callback decorator. They will now be logged as a warning (not printed) in both server types
- setup script now generates a bunch of console commands such as 'pyro4-ns' (previously you had to type 'python -m Pyro4.naming' etc.)
- made logger category names of the two socket servers consistent
- improved the clean shutdown mechanism of the daemon
- Daemon.register() now has a force argument that allows you to silently overwrite a previous registration of the object (if present)
- flame server methods _invokeBuiltin and _invokeModule renamed without underscores to follow the public exposed method name rule
- pep8'ified most of the source code
- documentation improvements
- linked to Travis CI: https://travis-ci.org/irmen/Pyro4


**Pyro 4.26**

- introduced PICKLE_PROTOCOL_VERSION config item
- fixed exception handling when dealing with different major Python versions. Using serpent or json now also properly translates exception objects even if the major Python version differ
- because of the new way Pyro deals with serialized exceptions, the wire protocol version was updated to 47. You'll have to update all Pyro4 libraries to 4.26
- name server prints a warning if a protocol error occurs (this helps to spot issues such as serializer protocol mismatches)
- more info in documentation about pickle and numpy
- improved documentation index


**Pyro 4.25**

- now also puts package name in serpent serialization data for custom class instances (previously only the class name was used)
- requires serpent 1.5 or newer (because of the feature above)
- support for (Linux) abstract namespace AF_UNIX sockets (with a 0-byte at the start of the name)
- register_dict_to_class method added on SerializerBase, to be able to deserialize to particular user defined classes
- docs: mention that you may have to install serpent manually (most notably with alternative Python implementations)
- docs: mention the serialization hooks on SerializerBase
- added ser_custom example that shows how to use the serialization hooks


**Pyro 4.24**

- Python 3.4 compatibility added (fixed pickle/marshal issues)
- a backwards incompatible change has been implemented regarding the threadpool implementation and configuration, see next two items.
- threadpool is now again a fixed size determined by the new THREADPOOL_SIZE config item (defaults to 16)
- config items removed: THREADPOOL_MINTHREADS, THREADPOOL_MAXTHREADS, THREADPOOL_IDLETIMEOUT
- daemon no longer sends an exception response when a communication error occurred (such as a timeout). This fixes the MSG_PING/disconnect example on linux
- jython: multiplex server type now available (uses select based multiplexing). Be wary, this has not been tested much. When in doubt, use the thread server type.
- python wheel distribution format support added (universal, setup.cfg)
- merged name server initd script improvements that were made for the Debian package (easy enable/disable, use sh instead of bash, etc)


**Pyro 4.23**

- Pyro4.test.echoserver now correctly runs the NS's broadcast server as well
- unix domain socket creation no longer fails when bind or connect address is unicode instead of str
- docs: added more info on dealing with new serialization configuration in existing code
- docs: improved name server documentation on registering objects
- docs: various small updates


**Pyro 4.22**

- support added in daemon to accept multiple serializers in incoming messages
- new config item added for that: SERIALIZERS_ACCEPTED (defaults to 'safe' serializers)
- wire protocol header changed. Not backwards compatible! New protocol version: 46.
- wire protocol: header now contains serializer used for the data payload
- wire protocol: header is extensible with optional 'annotations'. One is used for the HMAC digest
  that used to be in all messages even when the hmac option wasn't enabled.
- refactored core.MessageFactory: new submodule Pyro4.message. If you used MessageFactory
  in your own code you'll need to refactor it to use the new Pyro4.message.Message API instead.
- ``disconnects`` example client code updated to reflect this API change
- you can now write the protocol in URIs in lowercase if you want ("pyro:...") (will still be converted to uppercase)
- fixed poll server loop() not handling self.clients which caused crashes with a custom loopCondition
- fixed some unit test hang/timeout/crash issues
- improved unit tests for jython, disabled ipv6 tests for jython because of too many issues.
- improved unit tests for ironpython.


**Pyro 4.21**

- fixed denial of service vulnerabilities in socket servers
- MSG_PING message type added (internal server ping mechanism)
- disconnects example added that uses MSG_PING
- more exception types recognised in the serializers (such as GeneratorExit)
- fixed async regression when dealing with errors (properly serialize exceptionwrapper)
- fixed warehouse and stockmarket tutorials to work with new serializer logic
- fixed examples that didn't yet work with new serializer logic
- fixed unit tests to use unittest2 on Python 2.6
- no longer supports jython 2.5. You'll have to upgrade to jython 2.7.
- got rid of some byte/str handling cruft (because we no longer need to deal with jython 2.5)
- implemented autoproxy support for serpent and json serializers. It is not possible to do this for marshal.
- fixed serpent serialization problem with backslash escapes in unicode strings (requires serpent >= 1.3)


**Pyro 4.20**

.. note::
    The serializer-change is backwards-incompatible.
    You may have to change your remote object method contracts to deal with the
    changes. (or switch back to pickle if you can deal with its inherent security risk)

- multiple serializers supported instead of just pickle. (pickle, serpent, json, marshal)
  pickle is unsafe/unsecure, so a choice of safe/secure serializers is now available
- config item SERIALIZER added to select desired serializer, default is 'serpent'
- wire protocol version bumped because of this (45)
- config item LOGWIRE added to be able to see in the logfile what passes over the wire


**Pyro 4.18**

- IPV6 support landed in trunk (merged ipv6 branch)
- added config item PREFER_IP_VERSION  (4,6,0, default=4)
- socketutil.getIpVersion added
- socketutil.getMyIpAddress removed, use socketutil.getIpAddress("") instead
- socketutil.createSocket and createBroadcastSocket got new ipv6 argument to create ipv6 sockets instead of ipv4
- socketutil.bindOnUnusedPort now knows about ipv6 socket type as well
- Uri locations using numeric "[...]" ip-address notation are considered to be IPv6
- When Pyro displays a numeric IPv6 address in a Pyro uri, it will also use the "[...]" notation for the address
- Added ipv6 related unittests
- Added a few best-practices to the manual


**Pyro 4.17**

- Fixed possible IndentationError problem with sending modules in Flame
- Can now deal with exceptions that can't be serialized: they're raised as generic PyroError instead, with appropriate message
- added new config item FLAME_ENABLED, to enable/disable the use of Pyro Flame on the server. Default is false (disabled).
- Moved futures from core to new futures module. Code using Pyro4.Future will still work.
- Added python version info to configuration dump
- Made it more clear in the manual that you need to have the same major Python version on both sides


**Pyro 4.16**

- New implementation for the threadpool server: job queue with self-adjusting number of workers.
  The workaround that was in place (fixed pool size) has been removed.
- minor api doc fix: corrected reference of Pyro4 package members


**Pyro 4.15**

- Minimum threadpool size increased to 20 (from 4) to give a bit more breathing room
  while the threadpool scaling still needs to be fixed
- Binding a proxy will no longer release an existing connection first, instead it will just do nothing if the proxy has already been bound to its uri
- Resolved a race condition related to releasing and binding a proxy, improved unit test
- Documentation contains new homepage link
- No longer gives a warning about version incompatibility on Jython 2.5
- optimize bytecode flag no longer added in setup script when using jython, this used to crash the setup.py install process on jython
- fixed a gc issue due to a circular dependency
- IronPython: improved suggesting a free port number in socketutil.findProbablyUnusedPort
- IronPython: threadpoolserver no longer attempts to join the worker threads because not all threads seemed to actually exit on IronPython, thereby hanging the process when shutting down a daemon.
- Added a paragraph to tips&tricks about MSG_WAITALL
- socket.MSG_WAITALL is no longer deleted by importing Pyro on systems that have a broken MSG_WAITALL (Windows). You'll have to check for this yourself now, but I wanted to get rid of this side effect of importing Pyro.


**Pyro 4.14**

- Fixed source-newline incompatibility with sending module sources with flame, the
  fixExecSourceNewlines should be used on Python 3.0 and 3.1 as well it seemed.
- fix IronPython crash: set socketutil.setNoInherit to a dummy for IronPython
  because it can't pass the proper arguments to the win32 api call
- new config item MAX_MESSAGE_SIZE to optionally set a limit on the size of the
  messages sent on the wire, default=0 bytes (which means unlimited size).
- fixed some unit test problems with pypy and ironpython
- fixed some problems with MSG_WAITALL socket option on systems that don't properly support it
- temporary workaround for threadpool scaling problem (lock-up):
  pool is fixed at THREADPOOL_MINTHREADS threads, until the thread pool has been redesigned to get rid of the issues.


**Pyro 4.13**

- fixed source-newline problem with sending module sources with flame, this could break 
  on Python < 2.7 because exec is very picky about newlines in the source text on older pythons
- fixed URI and Proxy equality comparisons and hash(). Note that Proxy equality and hashing is
  done on the local proxy object and not on the remote Pyro object.
- added contrib directory where contributed stuff can be put. For now, there's a Linux init.d
  script for the name server daemon.
- fix setNoInherit on 64-bits Python on Windows (see http://tech.oyster.com/cherrypy-ctypes-and-being-explicit/)
- setting natport to 0 now replaces it by the internal port number, to facilitate one-to-one NAT port mapping setups
- fixed _pyroId attribute problem when running with Cython


**Pyro 4.12**

- added a few more code examples and cross-references to the docs to hopefully make it easier
  to understand what the different ways of connecting your client code and server objects are
- proxies no longer connect again if already connected (could happen with threads)
- fixed not-equal-comparison for uri and serializer objects (x!=y)


**Pyro 4.11**

- added host and port parameters to Daemon.serveSimple
- added nathost and natport parameters to Daemon to be able to run behind a NAT router/firewall
- added nathost and natport options to name server to configure it for use with NAT
- added NATHOST and NATPORT config items to configure the external address for use with NAT
- added BROADCAST_ADDRS config item. Use this to set the appropriate broadcast addresses (comma separated)
  The default is '<broadcast>' but you might need to change this on certain platforms (OpenSUSE?)
  where that doesn't work very well.
- changed logger category from Pyro to Pyro4
- connection closed error is no longer logged if it's just a normal terminated proxy connection
- fixed a config cleanup error in the test suite that could break it, depending on test execution order


**Pyro 4.10**

- added Future class that provides async (future) function calls for any callable (not just Pyro proxies)
- renamed _AsyncResult to FutureResult
- added Flame (foreign location automatic module exposer) in Pyro4.utils.flame, including docs and example
- Pyrolite also gained support for Flame (client access)
- improved FutureResult.then(), it now accepts additional normal arguments as well instead of only kwargs
- renamed Pyro4.config.refresh to Pyro4.config.reset because reset better describes what it is doing
- added parameter to config.refresh to make it ignore environment variables
- refactored internal threadpool into its own module, added unit tests


**Pyro 4.9**

- removed AsyncResultTimeout exception
- asyncresult.ready is now a property instead of a method
- asyncresult.wait() is a new method taking the optional timeout argument to wait for the result to become available.
  It doesn't raise an exception, instead it returns true or false.
- completed the documentation
- added gui_eventloop example
- added deadlock example
- added itunes example
- fixed some missing methods in the api reference documentation
- serialized data is released a bit faster to improve garbage collection
- fixed setting socket options in socketutil.createSocket
- socket SO_REUSEADDR option now not set anymore by default; added new config item SOCK_REUSE to be able to set it to True if you want.
- threaded server should deal with EINTR and other errors better (retry call)
- better closedown of threadpool server
- fix for potential autoproxy failure when unregistering pyro objects


**Pyro 4.8**

- Major additions to the documentation: tutorials, API docs, and much more.
- Polished many docstrings in the sources, they're used in the generation of the API docs.
- Unix domain socket support. Added :file:`unixdomainsock` example and unit tests.
- Added options to the name server and echo server to use Unix domain sockets.
- Name server broadcast responder will attempt to guess the caller's correct network
  interface, and use that to respond with the name server location IP (instead of 0.0.0.0).
  This should fix some problems that occurred when the nameserver was listening on
  0.0.0.0 and the proxy couldn't connect to it after lookup. Added unit test.
- API change: async callbacks have been changed into the more general async "call chain",
  using the ``then()`` method. Added examples and unit tests.
- Async calls now copy the proxy internally so they don't serialize after another anymore.
- A python 2.6 compatibility issue was fixed in the unit tests.

**Pyro 4.7**

- AutoProxy feature! This is a very nice one that I've always wanted to realize in Pyro ever since
  the early days. Now it's here: Pyro will automatically take care of any Pyro
  objects that you pass around through remote method calls. It will replace them
  by a proxy automatically, so the receiving side can call methods on it and be
  sure to talk to the remote object instead of a local copy. No more need to
  create a proxy object manually.
  This feature can be switched off using the config item ``AUTOPROXY`` to get the old behavior.
  Added a new :file:`autoproxy` example and changed several old examples to make use of this feature.
- Asynchronous method calls: you can execute a remote method (or a batch of remote method) asynchronously,
  and retrieve the results sometime in the future. Pyro will take care of collecting
  the return values in the background. Added :file:`async` example.
- One-line-server-setup using ``Pyro4.Daemon.serveSimple``, handy for quickly starting a server with basic settings.
- ``nameserver.register()`` behavior change: it will now overwrite an existing registration with the same name unless
  you provide a ``safe=True`` argument. This means you don't need to ``unregister()``
  your server objects anymore all the time when restarting the server.
- added ``Pyro4.util.excepthook`` that you can use for ``sys.excepthook``
- Part of the new manual has been written, including a tutorial where two simple applications are built.

**Pyro 4.6**

- Added batch call feature to greatly speed up many calls on the same proxy. Pyro can do 180,000 calls/sec or more with this.
- Fixed handling of connection fail in handshake
- A couple of python3 fixes related to the hmac key
- More unit test coverage

**Pyro 4.5**

- Added builtin test echo server, with example and unittest. Try ``python -m Pyro4.test.echoserver -h``
- Made ``Pyro4.config`` into a proper class with error checking.
- Some Jython related fixes.
- Code cleanups (pep8 is happier now)
- Fixed error behaviour, no longer crashes server in some cases
- ``HMAC_KEY`` is no longer required, but you'll still get a warning if you don't set it

**Pyro 4.4**

- removed pickle stream version check (too much overhead for too little benefit).
- set no-inherit flag on server socket to prevent problems with child processes blocking the socket. More info: http://www.cherrypy.org/ticket/856
- added HMAC message digests to the protocol, with a user configurable secret shared key in ``HMAC_KEY`` (required).
  This means you could now safely expose your Pyro interface to the outside world, without risk
  of getting owned by malicious messages constructed by a hacker.
  You need to have enough trust in your shared key. note that the data is not encrypted,
  it is only signed, so you still should not send sensitive data in plain text.
