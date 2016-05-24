**********
Change Log
**********

**Pyro 4.45**

- Dependency fix in setup/wheel/pip for selectors34 module.


**Pyro 4.44**

- *Behavior change:* when the threadpool server is used and it runs out of worker threads, clients attempting to connect
  now get a connection error telling them that the server threadpool has to be increased.
  On python 3.2 and newer a short timeout is used for the case that in the meantime a connection becomes available.
- THREADPOOL_ALLOW_QUEUE config item added. Enables you to choose for the previous
  blocking behavior when the threadpool server can no longer accept new connections. Defaults to False.
  *note: this is a temporary solution, in the next release a different threadpool implementation will be shipped
  for which this config item is no longer relevant. It will be removed again then.*
- Fixed 'malformed string' error when a Python 2 client talks to a Python 3 server;
  proxy metadata and nameserver metadata tags are no longer returned as a set but as a list.
  (This problem occurs in the serpent serializer because of a problem with the underlying ast.literal_eval function
  across different python versions)
- improved multiplex server, now uses best available selector on your platform (kqueue, epoll, etc)
  This was done by using the 'selectors' module, on older pythons (<3.4)
  the backport 'selectors34' has been added as a new requirement.
- added selector property on the daemon (to expose the multiplexing selector if that servertype is used).
- Added Daemon.combine() which merges different daemons' request loops and lets you just run the 'master daemon' requestLoop
- fixed import and test problems with IronPython (it doesn't like the dill serializer either, like pypy)
- Improved security when comparing HMAC codes (against timing attacks)
- added 'diffie-hellman' example to shows a way to approach server-client agreement on a shared secret key
- a few IronPython releated changes regarding str/bytes to decrease the number of special cases


**Pyro 4.43**

- improved docs on instance modes and instance creation
- improved cleanup of objects with instance_mode 'session', fixes possible memory leak
- fixed float vs None bug in rare situation when connecting socket gets a retryable error


**Pyro 4.42**

- added dill serialization support (https://pypi.python.org/pypi/dill)
- fixed dotted attribute client code in the ``attributes`` example
- handles EINTR signal and will continue the server loop now in this case, on Python 3.4 and newer.
- fixed async proxy calls not being done async, when metadata is used


**Pyro 4.41**

- fixed uri parsing bug in locateNS when trying to locate name server via unix domain socket
- fixed IronPython crash with Pyro4.core.current_context
- got rid of __slots__ on the URI class
- fixed output of nsc metadata string on Python 2.x
- sock_reuse option is now default on
- daemon now logs its pid when starting
- poll-server error handling now reflects the select server (swallow error when shutting down)


**Pyro 4.40**

- added python 3.5 to supported versions and configs
- support for metadata added to the name server (list of strings per registration).
  This provides a service like yellow-pages where you can query on category (for instance).
  You need to use memory or sqlite storage for this; the dbm storage doesn't support it.
- name server also has a new method set_metadata(), to set new metadata for an existing registration
- nsc tool has new commands to deal with metadata in the name server: setmeta, listmeta_all and listmeta_any
- removed obsolete stdinstdout example, it depended on exposing private attributes and Pyro hasn't allowed this anymore for quite some time (4.27)
- removed a problematic ipv6 unittest, and an often-failing workaround to determine the ipv6 address
- added ``current_context.client_sock_addr`` containing the address of the client doing the call
- current_context is now correct for oneway calls and async calls
- fixed some __copy__ methods to correctly deal with possible subclassing (Proxy)


**Pyro 4.39**

- dropped support for Python 2.6 and Python 3.2. Supported versions are now 2.7, 3.3, 3.4 and up.
- better exception when message size exceeds 2 gigabyte limit
- mentioned the 2 gigabyte message size limit in the docs
- added auto retry mechanism, MAX_RETRIES config item, and autoretry example.
- API CHANGE: the instance_creator function passed to @expose now get the class as a single parameter when invoked by Pyro
- removed test suite dependencies on unittest2 (was used for Python 2.6)
- greatly improved the messagebus example, it now contains a persistent storage as well
- can now deserialize sqlite3 exceptions as well (without the need of registering custom class serializers)
- serialized proxies now gets the timeout and retries properties from the active config settings rather than from the serialized data
- new MessageTooLargeError when the max message size is exceeded (subclesses ProtocolError, which was the old error thrown in this case)


**Pyro 4.38**

.. note::
    The below mentioned wire protocol change is backwards-incompatible.
    You have to update all your pyro libraries on clients and servers.
    (And Pyrolite libraries if you use them too)

- wire protocol version changed to 48 (new connection logic).
- changed the initial connection handshake protocol. Proxy and daemon now perform a handshake by exchanging data.
  You can set your own data on the proxy attribute ``_pyroHandshake``. You can override a proxy method ``_pyroValidateHandshake``
  and a daemon method ``validateHandshake`` to customize/validate the connection setup.
- drastically reduced the overhead of creating a new proxy connection by piggybacking the metadata on the
  connection response (this avoids a separate remote call to get_metadata). New proxy connections are ~50% faster.
- added ``Daemon.clientDisconnect()`` as a hook for when clients disconnect (``Daemon.validateHandshake`` can
  be used as the hook to handle new connections)
- you can now register a class on the Daemon instead of an object, and define instancing strategy: singleton, session, percall
- you can provide an optional factory method to create instances of your pyro server class when needed according to the instancing_strategy
- added handshake, instancemode and usersession examples
- added distributed-computing2 example
- added messagebus example
- fixed callcontext example daemon to actually return a custom annotation
- fixed benchmark/connections example
- httpgateway recognises ``X-Pyro-Correlation-Id`` http header on requests
- new mailing list address (``pyro@freelists.org``).  Bye bye Sourceforge.


**Pyro 4.37**

- added Pyro4.current_context global (thread-local) that contains various information about the client and the request
- added correlation id via the current_context so you can track what requests/responses belong together
- fixed hmac calculation on messages with more than one annotation
- proxy and daemon can now add custom annotations to messages
- httpgateway also sets correlation id and returns it to the browser via ``X-Pyro-Correlation-Id`` http header
- added callcontext example
- fixed error response seq nr and serializer id in case of error during the parsing of a message, previously they were bogus values


**Pyro 4.36**

- added SOCK_NODELAY config item to be able to turn the TCP_NODELAY socket option on (default is off).
- little cleanup of the intro example in the manual, and benchmark example
- added timezones example
- some clarifications added to the manual about serialization peculiarities
- serpent library dependency updated to 1.11, to profit from the performance improvements and float Inf/NaN support.
- pyrolite .net library now points to Nuget.org packages for download, and the java one to Maven.
- code blocks in manual updated to python 3 syntax


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


**Earlier versions**

Change history for earlier versions is available by looking at older versions of this file in the Github repo.
