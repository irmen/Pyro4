.. include:: <isonum.txt>

*********************
Upgrading from Pyro 3
*********************

.. _should-i-choose-pyro4:

Should I choose Pyro4?
======================

Should you use Pyro 4 or Pyro 3 for your project? This depends on a few things.

**Dependencies on older systems**

Pyro 4 has more modern system requirements than Pyro 3.
It is unsupported on Python versions below 2.6 (except Jython 2.5).
Pyro 3 runs fine on Python 2.5, and Pyro versions before 3.13 should run on even older Python versions.
So if you cannot use Python 2.6 or newer, you should use Pyro 3.

Pyro 4 has been written from scratch. While it looks and feels much like Pyro 3 did, its API and implementation are incompatible.
If you need to connect to existing systems that use Pyro 3, you can only do that with Pyro 3. Pyro 4 can't talk to them.

**Features**

Pyro 4 has several features that are not present in Pyro 3, but the reverse is also true.
If you require one of the following features for your system, you can only find them -for now- in Pyro 3:

- SSL support
- connection authentication
- mobile code
- remote attribute access
- Event server

Some of them may appear in the future in Pyro 4, but for now they're all exclusive to Pyro 3.

**Availability in package forms**

Some people can't or won't install software from source and rather use the package manager of their OS.
Pyro 4 might not yet be available in your package manager because it is rather new.
Pyro 3 is available as a Debian package.
So if you are on Debian (or a derivative like Ubuntu or Mint) and you only accept software from the distribution packages,
Pyro 3 is your only choice for now.

.. note::
    The Pyro project itself does not provide any OS-specific packaging.
    Things like the Debian Pyro package are created and maintained by
    different people (thanks for that!)

**Maturity**

Pyro 3 has been around for many years and has a proven track record. It also has a very stable API.
It only gets bug fixes and much effort is taken to keep it backward compatible with previous 3.x versions.
Pyro 4 on the other hand is still under active development.
The important API parts are more or less stabilized but as features are being added or changed, stuff might break.
So depending on your requirements of maturity and API stability you might choose one or the other.

Differences
===========

Here you can find what is different in Pyro4 compared to Pyro3.
This should help with converting existing Pyro3 applications to Pyro4.
It also serves as a quick overview for developers that are used to Pyro3,
to see what the new API and features of Pyro4 are like.

General differences from Pyro 3.x
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- Pyro4 requires Python 2.6 or newer. Pyro 3.x supports Python 2.5 (Pyro 3.12 and older, even support Python 2.4)
- Toplevel package name has been changed from ``Pyro`` into ``Pyro4``
- Mobile code support has been removed.
- Remote attribute access (``DynamicProxyWithAttrs``) has been removed (slight chance it appears again in the future in a different form)
- Event server has been removed (slight chance it appears again in the future in a different form).
- SSL support has been removed. Likely to appear again in a future version.
- You don't need to import the various sub packages. Just ``import Pyro4`` and you're done: the main Pyro API elements are available directly in the ``Pyro4`` package.
- ``Pyro.core.PyroURI`` has been renamed to ``Pyro4.URI``
- You can choose from two server types to use in your daemon, a threadpool server (that can process requests concurrently, most similar to Pyro3)
  and a select/poll based server (that processes requests in a single thread by multiplexing all client connections).
- Pyro objects in the daemon don't have a forced objectId UUID anymore. They just use the name you give them, or an auto generated one if you don't provide a name yourself.
- ``PYROLOC`` protocol has been removed. Just use the ``PYRO`` protocol with the logical name instead of the object id in the URI.
- Pyro daemon binds on a random free port by default, instead of on a fixed port. Name server still is on a fixed port by default.
- Pyro daemons (including the Name server) bind on localhost by default. This prevents exposure to the outside world in a default install.
  You have to explicitly tell Pyro4 to bind on another network interface. With Pyro3, it was the other way around,
  it would bind on all network interfaces by default (potentially exposing unwanted servers).
- Logging is done using Python's standard logging module instead of custom logger stuff from ``Pyro.util``. There is some autoconfig voodoo in the package init code that reacts to some environment variable settings.
- All classes are new style classes, so you can use super() etc. (this was already the case in the later Pyro 3.x releases but not in earlier ones)
- There are no batch files for the utilities (yet), but you can use aliases like this:
   | ``alias pyro-ns=python -m Pyro4.naming``
   | ``alias pyro-nsc=python -m Pyro4.nsc``
- The command line syntax of these tools has changed, just check out the new usage with '-h'.
- The name server doesn't have any groups anymore. The namespace is now 'flat'. You don't have to use the ':' in front of names, or separate parts using '.' anymore. You can look up names matching a prefix string or a regular expression now, so with clever names you can still achieve mostly the same as with the old group based namespace.
- The name server doesn't have a default group any longer. Name server proxies are regular Pyro proxies and don't perform any voodoo magic on the names anymore.
- Config items are in ``Pyro4.config`` (as they were in ``Pyro.config`` in Pyro3) but have changed quite a bit. Most of them have been removed. Some may return in a later version.
- Exception traceback processing: ``Pyro4.util.getPyroTraceback`` shouldn't be called with an exception object anymore. Either simply call it without parameters, or supply the usual ex_type, ex_value, ex_tb objects that you can get from sys.exc_info.
  Or even easier, install Pyro4's custom excepthook.

Client code differences
^^^^^^^^^^^^^^^^^^^^^^^
- ``Pyro.core.initClient`` was deprecated for a long time already, and has been removed.
- locating the name server: instead of ``locator=Pyro.naming.NameServerLocator(); ns=locator.getNS()`` simply use ``ns=Pyro4.locateNS()``
- Pyro's internal methods and attributes have been renamed and are all prefixed with ``_pyro``.
- getting the uri from a proxy: ``proxy.URI`` is now ``proxy._pyroUri``
- the ``Pyro.core.PyroURI`` object has changed quite a bit. It has been renamed to ``Pyro4.URI`` and many of its attributes are different. It knows two types of protocols: ``PYRO`` and ``PYRONAME`` (``PYROLOC`` has gone). The syntax is different too:  ``<protocol>:<objectid>@<location>``
- looking up stuff in the name server: ``ns.resolve`` is now ``ns.lookup``
- there is only one proxy class: ``Pyro4.Proxy``
- creating proxies: use the Proxy class constructor, pass in an URI or an uri string directly.
- rebinding a disconnected proxy: instead of ``obj.adapter.rebindURI`` now use: ``obj._pyroReconnect``
- proxies for 'meta' uris (``PYRONAME`` etc) are not updated anymore with the resolved uri. If you want the old behavior, you have to call ``proxy._pyroBind()`` explicitly to bind the proxy on the resolved PYRO uri.
- You can manually resolve a 'meta' uri by using ``Pyro4.resolve``, it will return a new normal PYRO uri.
- Oneway methods: ``proxy._setOneway`` got replaced by the ``proxy._pyroOneway`` attribute. That is a set (or sequence) so simply add method names to it that need to be oneway.

Server code differences
^^^^^^^^^^^^^^^^^^^^^^^
- ``Pyro.core.initServer`` was deprecated for a long time already, and has been removed.
- ``Pyro.core.ObjBase`` is gone, just use any class directly as a Pyro object. Pyro4 injects a few magic attributes in your object. Their names start with ``_pyro`` for easy identification.
- ``Pyro.core.SynchronizedObjBase`` is gone as well, you need to create your own thread safety measures if required (locks, Queues, etc)
- see above for changes concerning how to locate the name server.
- Daemons are created much in the same way as before. But they don't automagically register anything in the name server anymore so you have to do that yourself (``daemon.useNameServer`` is gone)
- Daemons now bind on a random free port by default instead of a fixed port. You need to specify a port yourself when creating a daemon if you want a fixed port.
- Daemons bind on localhost by default, instead of 0.0.0.0. If you want to expose to the network, you'll have to provide a proper hostname or ip address yourself. There are two utility methods in the ``Pyro4.socketutil`` module that can help you with that: ``getIpAddress`` and ``getMyIpAddress``.
- ``daemon.connect`` has been renamed to ``daemon.register``. It still returns the URI for the object, as usual.
- ``daemon.disconnect`` has been renamed to ``daemon.unregister``
- ``daemon.connectPersistent`` is gone, just pass the existing object id as a parameter to the normal register.
- getting an object's uri and registering in the name server: use the URI you got from the register call, or use ``daemon.uriFor`` to get a new URI for a given object. Use ``ns.register(objName, uri)`` as usual to register it in the name server.
- creating new pyro objects on the server and returning them (factory methods): ``server.getDaemon()`` is replaced by the ``_pyroDaemon`` attribute, and ``obj.getProxy()`` is gone. Typical pattern is now::

   uri=self._pyroDaemon.register(object)
   return Pyro4.Proxy(uri)

  **However** Pyro4 has an 'AUTOPROXY' feature (on by default) that makes the above unneeded (Pyro4 will wrap pyro objects with a proxy
  automatically for you). You can turn this feature off to make it look more like Pyro3's behavior.
- Unregistering objects from the daemon is done with ``some_pyro_object._pyroDaemon.unregister(some_pyro_object)`` (or use the object's URI).

New features
^^^^^^^^^^^^
Pyro4 introduces several new features that weren't available in Pyro3, so there is no migration path needed for those.
(Things like batched calls, async calls, new config items etc).
