**********
Change Log
**********

**Pyro 4.57**

- Pyro4.core.async() and proxy._pyroAsync() no longer return a copy of the proxy but rather modify the proxy itself,
  in an attempt to reduce the number of socket connections to a server. They still return the proxy object for api compatibility reasons.
- async result now internally retries connection after a short delay, if it finds that the server has no free worker threads to accept the connection.
  If COMMTIMEOUT has been set, it retries until the timeout is exceeded. Otherwise it retries indefinitely util it gets a connection.
- _StreamResultIterator now stops all communication as soon as StopIteration occurred, this avoids unnecessary close calls to remote iterators.


**Pyro 4.56**

- optional msgpack serializer added (requires msgpack-python library, see https://pypi.python.org/pypi/msgpack-python )
- fixed possible crash in closing of remote iterators (they could crash the proxy by screwing up the internal sequence number).
- json serializer can now serialize uuid.UUID, datetime and decimal objects (into strings, like serpent does)
- serializers can now deal with memoryview and bytearray serialized data input types.
- serpent library dependency updated to 1.19 to be able to deal with memoryview and bytearray inputs.
- added ``response_annotations`` on the call context object to be able to access annotations more easily than having to subclass Proxy or Daemon.
- ``Proxy._pyroAnnotations`` and ``Daemon.annotations`` no longer needs to call super, the annotations you return
  here are now automatically merged with whatever Pyro uses internally.
- Proxy and Daemon now contain the ip address family in their repr string.
- Pyro now logs the ip address family for proxy or daemon socket connections.
- ipv6 doesn't have broadcasts, so Pyro no longer uses them when ipv6 is in use.
- improved the docs about binary data transfer a bit.
- documentation is now also available on ReadTheDocs: http://pyro4.readthedocs.io/
- fixed various examples


**Pyro 4.55**

- *CRITICAL FIX:* serpent library dependency updated to 1.17 to fix issues with encoding and parsing strings containing 0-bytes.
  Note that if you don't want to upgrade Pyro itself yet, you should manually upgrade the serpent library to get this fix.
- Prefer selectors2 over selectors34 if it is available (Python 3.4 or older, to have better semantics of failing syscalls)
- Removed THREADING2 config item and Pyro4.threadutil module. (the threading2 third party module is old and seems unmaintained and wasn't useful for Pyro anyway)
- Improved module structure; fixed various circular import dependencies. This also fixed the RuntimeWarning about sys.modules, when starting the name server.
- To achieve the previous item, had to move ``resolve`` and ``locateNS`` from ``Pyro4.naming`` to ``Pyro4.core`` .
  They're still available on their old location for backwards compatibility for now.
  Ofcourse, they're also still on their old "shortcut" location in ``Pyro4`` directly.
- Removed the publicly visible serializer id numbers from the message module. They're internal protocol details, user code should always refer to serializers by their name.
- When a connection cannot be made, the address Pyro tries to connect to is now also included in the error message.
- Added overridable ``Daemon.housekeeping()`` method.
- Improved error message in case of invalid ipv6 uri.
- Fixed various examples, and made the Pyro4 main api package documentation page complete again.


**Pyro 4.54**

- Serpent serializer: floats with value NaN will now be properly serialized and deserialized into a float again, instead of the class dict ``{'__class__':'float', 'value':'nan'}``
  Note that you can achieve the same for older versions of Pyro by manually registering a custom converter:
  ``Pyro4.util.SerializerBase.register_dict_to_class("float", lambda _, d: float(d["value"]))``
- Removed platform checks when using dill serializer, latest Pypy version + latest dill (0.2.6) should work again.
  Other platforms might still expose problems when trying to use dill (IronPython), but they are now considered
  to be the user's problem if they attempt to use this combination.
- Applied version detection patch from Debian package to contrib/init.d/pyro4-nsd
- Don't crash immediately at importing Pyro4 when the 'selectors' or 'selectors34' module is not available.
  Rationale:
  This is normally a required dependency so the situation should usually not occur at all.
  But it can be problematic on Debian (and perhaps other distributions) at this time, because this module may not be packaged/not be available.
  So we now raise a proper error message, but only when an attempt is made to actually create a multiplex server (all other parts of Pyro4 are still usable just fine in this case).
  The selectors module is available automatically on Python 3.4 or newer, for older Pythons you have to
  install it manually or via the python2-selectors34 package if that is available.
- Fixed crash when trying to print the repr or string form of a Daemon that was serialized.
- Changed uuid.uuid1() calls to uuid.uuid4()  because of potential issues with uuid1 (obscure resource leak on file descriptors on /var/lib/libuuid/clock.txt).
  Pyro4 already used uuid4() for certain things, it now exclusively uses uuid4().
- Fixed a few IronPython issues with several unit tests.
- Improved the installation chapter in the docs.


**Pyro 4.53**

- *CRITICAL FIX:* serpent library dependency updated to 1.16 to fix floating point precision loss error on older python versions.
  Note that if you don't want to upgrade Pyro itself yet, you should manually upgrade the serpent library to get this fix.
- added unittest to check that float precision is maintained in the serializers
- fixed some typos in docs and docstrings, improved daemon metadata doc.
- mailing list (``pyro@freelists.org``) has been discontinued.


**Pyro 4.52**

- fixed Python 3.6 compatibility issue in name server when using sqlite storage ("cannot VACUUM from within a transaction")
- fixed Python 3.6 ResourceWarning in unit test
- Python 3.6 added to travis CI build
- fixed possible crash on Python 2.x when shutting down a daemon from within a Pyro server object itself (because it tried to join its own thread)
- sensible error is raised again in client when threadpool server can't accept any more new connections (regression since 4.50)
- daemon has new ``resetMetadataCache`` method to be used when the set of exposed members of your Pyro class changes during runtime
- better testcases for properly handling handshake error reasons


**Pyro 4.51**

- added PYROMETA magic URI protocol, to look up an object with the given metadata tags (yellow-page lookup rather than by name)
  Example: ``Pyro4.Proxy("PYROMETA:metatag1,metatag2")``
- added distributed-computing3 example to show simple work load distribution using PYROMETA object discovery
- fixed unlikely but possible crash in logging statement when client disconnects from multiplex server


**Pyro 4.50**

- new ITER_STREAM_LINGER config item to keep streams alive for a given period after proxy disconnect (defaults to 30 sec.)
- new NS_AUTOCLEAN config item to set a recurring period in seconds where the Name server checks its registrations.
  It will then auto cleanup registrations after a short while if they're no longer available. (defaults to 0.0 - disabled).
- Future can now be given a delay before it is evaluated
- Future can now be cancelled (if it hasn't been evalued yet)


**Pyro 4.49**

- added iterator item streaming support. It is now possible to return iterators from a remote
  call or even call a remote generator function, and iterate over it in the client.
  Items will be retrieved on demand from the server.
- new ITER_STREAMING config item to disable or enable streaming support in the server (default=enabled)
- new ITER_STREAM_LIFETIME config item to be able to set a maximum lifetime for item streams (default=no limit)
- the iter streaming is supported for Java and .NET in Pyrolite 4.14 as well
- new simplified stockquotes example using generators instead of callbacks
- changed daemon shutdown mechanism again to not use separate thread anymore, fixes thread leak
- serpent library dependency updated to 1.15


**Pyro 4.48**

- The threaded socket server now adapts the number of threads dynamically depending on connection count.
  This resolves the problem where your clients freeze because the server ran out of free connections
  When all threads are busy, new connections will fail with an exception.
- THREADPOOL_SIZE_MIN config item added to specify the min number of threads (defaults to 4)
- THREADPOOL_SIZE increased to 40 (was 16, and no longer allocates all these threads upfront)
- THREADPOOL_ALLOW_QUEUE config item removed, it is no longer relevant
- made the repr strings use semicolons instead of comma as separator to avoid confusion when printed in lists
- added per proxy serializer override by setting proxy._pyroSerializer
- added distributed-mandelbrot example that shows ascii animation and picture of the mandelbrot fractal set
- fixed timeout when locating name server on 127.0.1.1 on systems that don't use that address (osx)
- fixed ResourceWarning in socketutil.createSocket; socket that could not be connected is properly closed now


**Pyro 4.47**

- *Backwards incompatible change:* As announced in the previous version, the instance_mode and instance_creator
  parameters have now been removed from the @expose decorator.  Use @behavior to specify them instead on your classes.
- The default instance mode when using @expose on the class and not using @behavior, is now also 'session'
  (was 'single').   Note that when you used @behavior with its default argument or only @expose on methods,
  the instance mode of the class already was 'session'.
  If your code really requires the pyro object to be a singleton, add an explicit
  @behavior(instance_mode="single") to that class. You can already start doing this while still using Pyro 4.46 and
  then upgrade the library once you've converted everything.
- Name server lookup now also considers 127.0.1.1 when trying to find a name server on localhost.
  This is convenient on some systems (Debian Linux) where 127.0.1.1 is often the address assigned
  to the local system via the hosts file.
- fixed multiplex server shutdown sometimes hanging
- fixed crash that sometimes occurred in daemon shutdown
- fixed crash that sometimes occurred when releasing and reconnecting the proxy from different threads


**Pyro 4.46**

.. note::
    Compatibility issue:
    The change mentioned below about ``@expose`` now being required by default
    requires a change in your (server-)code or configuration. Read on for details.

.. note::
    Using ``@expose(...)`` on a class to set the ``instance_mode`` or/and ``instance_creator`` for that
    class, also exposes ALL methods of that class. That is an unintended side-effect that will be fixed
    in the next Pyro version. You can already fix your code right now to prepare for this. Read on for details.

- ``@Pyro4.behavior`` decorator added that should now be used to set instance_mode and instance_creator instead of
  using ``@Pyro4.expose``.  You can still use ``@expose`` in this release, but its arguments will be removed
  in the next Pyro version.  So by then you have to have updated your code or it won't run anymore.
  The fix is simple: replace all occurences of ``@expose(...)`` *where you set the ``instance_mode`` or/and ``instance_creator``*
  on your Pyro class, by ``@behavior(...)`` -- and add new ``@expose`` decorations to the class or the methods
  as required to properly expose them. Also read the next bullet.
- *Backwards incompatible behavior change:* in the spirit of 'secure by default', it's now required to use ``@expose``
  on things you want to expose via Pyro. This is because the REQUIRE_EXPOSE config item is now True by default.
  The "servers" chapter contains details about this and how you can best approach this upgrade issue.
- blobtransfer example added.
- improved the docs on binary data transfer a bit.
- code now uses set literals instead of old fashioned set([...])
- removed the way outdated 'upgrading from Pyro3' chapter from the documentation.
- Pyro4.util.get_exposed_members now has a cache which speeds up determining object metadata enormously on subsequent connections.
- added paragraph to server chapter in documentation about how to expose classes without changing the source code (such as 3rd party libraries)
- added thirdpartylib example for the above


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


**Earlier versions**

Change history for earlier versions is available by looking at older versions of this file in the Github source repository.
