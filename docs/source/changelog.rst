**********
Change Log
**********

**Pyro 4.71**

- updated ``msgpack`` dependency (was ``msgpack-python`` but that name is now deprecated)
- fixed restart and force reload commands of the contrib/init.d/pyro4-nsd script, and changed its port binding
  from 9999 back to 9090 which is Pyro's default.
- serpent 1.24 library now required to fix some api deprecation warnings when using Python 3.7 or newer.


**Pyro 4.70**

- bump to version 4.70 to emphasize the following change:
- **incompatible API change** for python 3.7 compatibility: renaming of ``async`` function and keyword arguments in the API:
  Renamed ``Pyro4.core.async`` to ``Pyro4.core.asyncproxy`` (and its occurrence in ``Pyro4``)
  and the ``async`` keyword argument in some methods to ``asynchronous``.
  This had to be done because ``async`` (and ``await``) are now parsed as keywords in Python 3.7 and using them otherwise will result
  in a SyntaxError when loading the module.
  It is suggested you stop using the ``asyncproxy`` function and instead create asynchronous proxies using the ``_pyroAsync``
  method on the regular proxy.
- For existing code running on Python *older than 3.7*, a backwards compatibility feature is present to still provide the
  ``async`` function and keyword arguments as they were supported on previous Pyro versions.
  But also for that older environments, it's advised to migrate away from them and start using the new names.
- Proxy and Daemon have a new 'connected_socket' parameter. You can set it to a user-supplied connected socket that must
  be used by them instead of creating a new socket for you. Connected sockets can be created using the socket.socketpair()
  function for instance, and allow for easy and efficient communication over an internal socket between
  parent-child processes or threads, using Pyro.  Also see the new 'socketpair' example.
- dropped support for Python 3.3 (which has reached end-of-life status). Supported Python versions are now 2.7, and 3.4 or newer.
  (the life cycle status of the Python versions can be seen here https://devguide.python.org/#status-of-python-branches)


**Pyro 4.63**

- fixed bug in autoproxy logic where it registered the wrong type if daemon.register() was called with
  a class instead of an object (internal register_type_replacement method)
- added check in @expose method to validate the order of decorators on a method (@expose should come last,
  after @classmethod or @staticmethod).
- added resource tracking feature (see 'Automatically freeing resources when client connection gets closed' in the Tips & Tricks chapter)
- the warning about a class not exposing anything now actually tells you the correct class


**Pyro 4.62**

- **major new feature: SSL/TLS support added** - a handful of new config items ('SSL' prefixed), supports
  server-only certificate and also 2-way-ssl (server+client certificates).
  For testing purposes, self-signed server and client certificates are available in the 'certs' directory.
  SSL/TLS in Pyro is supported on Python 2.7.11+ or Python 3.4.4+
  (these versions have various important security related changes such as disabling vulnerable cyphers or protocols by default)
- added SSL example that shows how to configure 2-way-SSL in Pyro and how to do certificate verification on both sides.
- added cloudpickle serialization support (https://github.com/cloudpipe/cloudpickle/)
- added a small extended-pickle example that shows what dill and cloudpickle can do (send actual functions)
- daemon is now more resilient to exceptions occurring with socket communications (it logs them but is otherwise not interrupted)
  (this was required to avoid errors occurring in the SSL layer stopping the server)
- some small bugs fixed (crash when logging certain errors in thread server, invalid protected members showing up on pypy3)
- the ``raise data`` line in a traceback coming from Pyro now has a comment after it,
  telling you that you probably should inspect the remote traceback as well.
- *note*: if you're using Python 3 only and are interested in a modernized version of Pyro,
  have a look at Pyro5: https://github.com/irmen/Pyro5  It's experimental work in progress, but it works pretty well.
- *note*: Pyro4 is reaching a state where I consider it "feature complete":
  I'm considering not adding more new features but only doing bug-fixes.
  New features (if any) will then appear only in Pyro5.


**Pyro 4.61**

- serpent 1.23 library now required.
- Pyro4.utils.flame.connect now has an optional ``hmac_key`` argument. You can now use this
  utility function to connect to a flame server running with a hmac_key. (Previously it didn't
  let you specify the client hmac_key so you had to create a flame proxy manually, on which you
  then had to set the _pyroHmacKey property).
- main documentation is now http://pyro4.readthedocs.io instead of http://pythonhosted.org/Pyro4/


**Pyro 4.60**

- ``Pyro4.core.async()`` and ``proxy._pyroAsync()`` now return ``None``, instead of the proxy object.
  This means you'll have to change your code that expects a proxy as return value, for instance by creating a
  copy of the proxy yourself first.
  This change was done to avoid subtle errors where older code still assumed it got a *copy* of the proxy,
  but since 4.57 that is no longer done and it is handed back the same proxy.
  By returning ``None`` now, at least the old code will now crash with a clear error, instead of silently continuing
  with the possibility of failing in weird ways later.


**Pyro 4.59**

- Fixed pyro4-check-config script.


**Pyro 4.58**

- Added feature to be able to pass through serialized arguments unchanged via ``Pyro4.core.SerializedBlob``, see example 'blob-dispatch'
- Fixed a fair amount of typos in the manual and readme texts.
- The stockquotes tutorial example now also has a 'phase 3' just like the warehouse tutorial example, to show how to run it on different machines.


**Pyro 4.57**

- Pyro4.core.async() and proxy._pyroAsync() no longer return a copy of the proxy but rather modify the proxy itself,
  in an attempt to reduce the number of socket connections to a server. They still return the proxy object for api compatibility reasons.
- async result now internally retries connection after a short delay, if it finds that the server has no free worker threads to accept the connection.
  If COMMTIMEOUT has been set, it retries until the timeout is exceeded. Otherwise it retries indefinitely util it gets a connection.
- _StreamResultIterator now stops all communication as soon as StopIteration occurred, this avoids unnecessary close calls to remote iterators.


**Pyro 4.56**

- optional msgpack serializer added (requires msgpack library, see https://pypi.python.org/pypi/msgpack )
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
  Of course, they're also still on their old "shortcut" location in ``Pyro4`` directly.
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



**Earlier versions**

Change history for earlier versions is available by looking at older versions of this documentation.
One way to do that is looking at previous versions in the Github source repository.
