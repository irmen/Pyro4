**********
Change Log
**********

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
