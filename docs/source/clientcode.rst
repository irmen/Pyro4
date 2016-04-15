.. index:: client code, calling remote objects

*******************************
Clients: Calling remote objects
*******************************

This chapter explains how you write code that calls remote objects.
Often, a program that calls methods on a Pyro object is called a *client* program.
(The program that provides the object and actually runs the methods, is the *server*.
Both roles can be mixed in a single program.)

Make sure you are familiar with Pyro's :ref:`keyconcepts` before reading on.


.. index:: object discovery, location, object name

.. _object-discovery:

Object discovery
================

To be able to call methods on a Pyro object, you have to tell Pyro where it can find
the actual object. This is done by creating an appropriate URI, which contains amongst
others the object name and the location where it can be found.
You can create it in a number of ways.

* directly use the object name and location.
    This is the easiest way and you write an URI directly like this: ``PYRO:someobjectid@servername:9999``
    It requires that you already know the object id, servername, and port number.
    You could choose to use fixed object names and fixed port numbers to connect Pyro daemons on.
    For instance, you could decide that your music server object is always called "musicserver",
    and is accessible on port 9999 on your server musicbox.my.lan. You could then simply use::

        uri_string = "PYRO:musicserver@musicbox.my.lan:9999"
        # or use Pyro4.URI("...") for an URI object instead of a string

    Most examples that come with Pyro simply ask the user to type this in on the command line,
    based on what the server printed. This is not very useful for real programs,
    but it is a simple way to make it work. You could write the information to a file
    and read that from a file share (only slightly more useful, but it's just an idea).

* use a logical name and look it up in the name server.
    A more flexible way of locating your objects is using logical names for them and storing
    those in the Pyro name server. Remember that the name server is like a phone book, you look
    up a name and it gives you the exact location.
    To continue on the previous bullet, this means your clients would only have to know the
    logical name "musicserver". They can then use the name server to obtain the proper URI::

        import Pyro4
        nameserver = Pyro4.locateNS()
        uri = nameserver.lookup("musicserver")
        # ... uri now contains the URI with actual location of the musicserver object

    You might wonder how Pyro finds the Name server. This is explained in the separate chapter :doc:`nameserver`.

* use a logical name and let Pyro look it up in the name server for you.
    Very similar to the option above, but even more convenient, is using the *meta*-protocol
    identifier ``PYRONAME`` in your URI string. It lets Pyro know that it should lookup
    the name following it, in the name server. Pyro should then
    use the resulting URI from the name server to contact the actual object.
    See :ref:`nameserver-pyroname`.
    This means you can write::

        uri_string = "PYRONAME:musicserver"
        # or Pyro4.URI("PYRONAME:musicserver") for an URI object

    You can use this URI everywhere you would normally use a normal uri (using ``PYRO``).
    Everytime Pyro encounters the ``PYRONAME`` uri it will use the name server automatically
    to look up the object for you. [#pyroname]_

.. [#pyroname] this is not very efficient if it occurs often. Have a look at the :doc:`tipstricks`
   chapter for some hints about this.


.. index::
    double: Proxy; calling methods

Calling methods
===============
Once you have the location of the Pyro object you want to talk to, you create a Proxy for it.
Normally you would perhaps create an instance of a class, and invoke methods on that object.
But with Pyro, your remote method calls on Pyro objects go trough a proxy.
The proxy can be treated as if it was the actual object, so you write normal python code
to call the remote methods and deal with the return values, or even exceptions::

    # Continuing our imaginary music server example.
    # Assume that uri contains the uri for the music server object.

    musicserver = Pyro4.Proxy(uri)
    try:
        musicserver.load_playlist("90s rock")
        musicserver.play()
        print("Currently playing:", musicserver.current_song())
    except MediaServerException:
        print("Couldn't select playlist or start playing")

For normal usage, there's not a single line of Pyro specific code once you have a proxy!


.. index::
    single: object serialization
    double: serialization; pickle
    double: serialization; dill
    double: serialization; serpent
    double: serialization; marshal
    double: serialization; json


.. index::
    double: Proxy; remote attributes

Accessing remote attributes
===========================
You can access exposed attributes of your remote objects directly via the proxy.
If you try to access an undefined or unexposed attribute, the proxy will raise an AttributeError stating the problem.
Note that direct remote attribute access only works if the metadata feature is enabled (``METADATA`` config item, enabled by default).
::

    import Pyro4

    p = Pyro4.Proxy("...")
    velo = p.velocity    # attribute access, no method call
    print("velocity = ", velo)


See the :file:`attributes` example for more information.



.. _object-serialization:

Serialization
=============

Pyro will serialize the objects that you pass to the remote methods, so they can be sent across
a network connection. Depending on the serializer that is being used, there will be some limitations
on what objects you can use.

* serpent: serializes into Python literal expressions. Accepts quite a lot of different types.
  Many will be serialized as dicts. You might need to explicitly translate literals back to specific types
  on the receiving end if so desired, because most custom classes aren't dealt with automatically.
  Requires third party library module, but it will be installed automatically as a dependency of Pyro.
  This serializer is the default choice.
* json: more restricted as serpent, less types supported. Part of the standard library. Not particularly fast,
  so you might want to look for a faster 3rd party implementation (such as simplejson). Be sure to benchmark before switching!
  Use the `JSON_MODULE` config item to tell Pyro to use the other module instead. Note that it has to support
  the advanced parameters such as `default`, not all 3rd party implementations do that.
* marshal: a very limited but fast serializer. Can deal with a small range of builtin types only,
  no custom classes can be serialized. Part of the standard library.
* pickle: the legacy serializer. Fast and supports almost all types. Has security problems though. Part
  of the standard library. No longer used by default.
* dill: See https://pypi.python.org/pypi/dill It is similar to pickle serializer, but more capable. Extends python's 'pickle' module
  for serializing and de-serializing python objects to the majority of the built-in python types.
  Has security problems though, just as pickle.

.. index:: SERIALIZER, PICKLE_PROTOCOL_VERSION, SERIALIZERS_ACCEPTED, DILL_PROTOCOL_VERSION

You select the serializer to be used by setting the ``SERIALIZER`` config item. (See the :doc:`/config` chapter).
The valid choices are the names of the serializer from the list mentioned above.
If you're using pickle or dill, and need to control the protocol version that is used,
you can do so with the ``PICKLE_PROTOCOL_VERSION`` or ``DILL_PROTOCOL_VERSION`` config items.
By default Pyro will use the highest one available.

.. note::
    Since Pyro 4.20 the default serializer is "``serpent``". Serpent is secure but cannot
    serialize all types (by design). Some types are serialized into a different form such as
    a string or a dict. Strings are serialized/deserialized into unicode at all times -- be aware
    of this if you're using Python 2.x (strings in Python 3.x are always unicode already).

.. note::
    The serializer(s) that a Pyro server/daemon accepts, is controlled by a different
    config item (``SERIALIZERS_ACCEPTED``). This can be a set of one or more serializers.
    By default it accepts the set of 'safe' serializers, so "``pickle``" and "``dill``" are excluded.
    If the server doesn't accept the serializer that you configured
    for your client, it will refuse the requests and respond with an exception that tells
    you about the unsupported serializer choice. If it *does* accept your requests,
    the server response will use the same serializer that was used for the request.

.. note::
    Because the name server is just a regular Pyro server as well, you will have to tell
    it to allow the pickle or dill serializers if your client code uses them.
    See :ref:`nameserver-pickle` and :ref:`nameserver-dill`.


.. index:: deserialization, serializing custom classes, deserializing custom classes

.. _customizing-serialization:

Changing the way your custom classes are (de)serialized
-------------------------------------------------------

.. note::
    The information in this paragraph applies only when you're not using the pickle nor dill
    serialization protocols.

By default, custom classes are serialized into a dict.
They are not deserialized back into instances of your custom class. This avoids possible security issues.
An exception to this however are certain classes in the Pyro4 package itself (such as the URI and Proxy classes).
They *are* deserialized back into objects of that certain class, because they are critical for Pyro to function correctly.

There are a few hooks however that allow you to extend this default behaviour and register certain custom
converter functions. These allow you to change the way your custom classes are treated, and allow you
to actually get instances of your custom class back from the deserialization if you so desire.

The hooks are provided via several classmethods:
    :py:meth:`Pyro4.util.SerializerBase.register_class_to_dict` and :py:meth:`Pyro4.util.SerializerBase.register_dict_to_class`

and their unregister-counterparts:
    :py:meth:`Pyro4.util.SerializerBase.unregister_class_to_dict` and :py:meth:`Pyro4.util.SerializerBase.unregister_dict_to_class`

Click on the method link to see its apidoc, or have a look at the :file:`ser_custom` example and the :file:`test_serialize` unit tests for more information.
It is recommended to avoid using these hooks if possible, there's a security risk
to create arbitrary objects from serialized data that is received from untrusted sources.


Upgrading older code that relies on pickle
------------------------------------------

What do you have to do with code that relies on pickle, and worked fine in older Pyro versions, but now crashes?

You have three options:

#. Redesign remote interfaces
#. Configure Pyro to eable the use of pickle again
#. Stick to Pyro 4.18 (less preferable)

You can redesign the remote interface to only include types that can be serialized (python's built-in types and
exception classes, and a few Pyro specific classes such as URIs). That way you benefit from the new security that
the alternative serializers provide. If you can't do this, you have to tell Pyro to enable pickle again.
This has been made an explicit step because of the security implications of using pickle. Here's how to do this:

Client code configuration
    Tell Pyro to use pickle as serializer for outgoing communication, by setting the ``SERIALIZER``
    config item to ``pickle``. For instance, in your code: :code:`Pyro4.config.SERIALIZER = 'pickle'`
    or set the appropriate environment variable.

Server code configuration
    Tell Pyro to accept pickle as incoming serialization format, by including ``pickle`` in
    the ``SERIALIZERS_ACCEPTED`` config item list. For instance, in your code:
    :code:`Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')`. Or set the appropriate
    environment variable, for instance: :code:`export PYRO_SERIALIZERS_ACCEPTED=serpent,json,marshal,pickle`.
    If your server also uses Pyro to call other servers, you may also need to configure
    it as mentioned above at 'client code'. This is because the incoming and outgoing serializer formats
    are configured independently.


.. index:: release proxy connection
.. index::
    double: Proxy; cleaning up
.. _client_cleanup:

Proxies, connections, threads and cleaning up
=============================================
Here are some rules:

* Every single Proxy object will have its own socket connection to the daemon.
* You can share Proxy objects among threads, it will re-use the same socket connection.
* Usually every connection in the daemon has its own processing thread there, but for more details see the :doc:`servercode` chapter.
* The connection will remain active for the lifetime of the proxy object. Hence, consider cleaning up a proxy object explicitly
  if you know you won't be using it again in a while. That will free up resources and socket connections.
  You can do this in two ways:

  1. calling ``_pyroRelease()`` on the proxy.
  2. using the proxy as a context manager in a ``with`` statement.
     This ensures that when you're done with it, or an error occurs (inside the with-block),
     the connection is released::

        with Pyro4.Proxy(".....") as obj:
            obj.method()

  *Note:* you can still use the proxy object when it is disconnected: Pyro will reconnect it as soon as it's needed again.
* At proxy creation, no actual connection is made. The proxy is only actually connected at first use, or when you manually
  connect it using the ``_pyroReconnect()`` or ``_pyroBind()`` methods.


.. index::
    double: oneway; client method call

.. _oneway-calls-client:

Oneway calls
============

Normal method calls always block until the response is returned. This can be any normal return value, ``None``,
or an error in the form of a raised exception. The client code execution is suspended until the method call
has finished and produced its result.

Some methods never return any response or you are simply not interested in it (including errors and
exceptions!), or you don't want to wait until the result is available but rather continue immediately.
You can tell Pyro that calls to these methods should be done as *one-way calls*.
For calls to such methods, Pyro will not wait for a response from the remote object.
The return value of these calls is always ``None``, which is returned *immediately* after submitting the method
invocation to the server. The server will process the call while your client continues execution.
The client can't tell if the method call was successful, because no return value, no errors and no exceptions will be returned!
If you want to find out later what - if anything - happened, you have to call another (non-oneway) method that does return a value.

Note that this is different from :ref:`async-calls`: they are also executed while your client code
continues with its work, but they *do* return a value (but at a later moment in time). Oneway calls
are more efficient because they immediately produce ``None`` as result and that's it.

.. index::
    double: @Pyro4.oneway; client handling

**How to make methods one-way:**
You mark the methods of your class *in the server* as one-way by using a special *decorator*.
See :ref:`decorating-pyro-class` for details on how to do this.
See the :file:`oneway` example for some code that demonstrates the use of oneway methods.


.. index:: batch calls

.. _batched-calls:

Batched calls
=============
Doing many small remote method calls in sequence has a fair amount of latency and overhead.
Pyro provides a means to gather all these small calls and submit it as a single 'batched call'.
When the server processed them all, you get back all results at once.
Depending on the size of the arguments, the network speed, and the amount of calls,
doing a batched call can be *much* faster than invoking every call by itself.
Note that this feature is only available for calls on the same proxy object.

How it works:

#. You create a batch proxy object for the proxy object.
#. Call all the methods you would normally call on the regular proxy, but use the batch proxy object instead.
#. Call the batch proxy object itself to obtain the generator with the results.

You create a batch proxy using this: ``batch = Pyro4.batch(proxy)`` or this (equivalent): ``batch = proxy._pyroBatch()``.
The signature of the batch proxy call is as follows:

.. py:method:: batchproxy.__call__([oneway=False, async=False])

    Invoke the batch and when done, returns a generator that produces the results of every call, in order.
    If ``oneway==True``, perform the whole batch as one-way calls, and return ``None`` immediately.
    If ``async==True``, perform the batch asynchronously, and return an asynchronous call result object immediately.
    
**Simple example**::

    batch = Pyro4.batch(proxy)
    batch.method1()
    batch.method2()
    # more calls ...
    batch.methodN()
    results = batch()   # execute the batch
    for result in results:
        print(result)   # process result in order of calls...

**Oneway batch**::

    results = batch(oneway=True)
    # results==None

**Asynchronous batch**

The result value of an asynchronous batch call is a special object. See :ref:`async-calls` for more details about it.
This is some simple code doing an asynchronous batch::

    results = batch(async=True)
    # do some stuff... until you're ready and require the results of the async batch:
    for result in results.value:
        print(result)    # process the results


See the :file:`batchedcalls` example for more details.


.. index:: async call, future, call chaining

.. _async-calls:

Asynchronous ('future') remote calls & call chains
==================================================
You can execute a remote method call and tell Pyro: "hey, I don't need the results right now.
Go ahead and compute them, I'll come back later once I need them".
The call will be processed in the background and you can collect the results at a later time.
If the results are not yet available (because the call is *still* being processed) your code blocks
but only at the line you are actually retrieving the results. If they have become available in the
meantime, the code doesn't block at all and can process the results immediately.
It is possible to define one or more callables (the "call chain") that should be invoked
automatically by Pyro as soon as the result value becomes available.

You create an async proxy using this: ``async = Pyro4.async(proxy)`` or this (equivalent): ``async = proxy._pyroAsync()``.
Every remote method call you make on the async proxy, returns a
:py:class:`Pyro4.futures.FutureResult` object immediately.
This object means 'the result of this will be available at some moment in the future' and has the following interface:

.. py:attribute:: value

    This property contains the result value from the call.
    If you read this and the value is not yet available, execution is halted until the value becomes available.
    If it is already available you can read it as usual.

.. py:attribute:: ready

    This property contains the readiness of the result value (``True`` meaning that the value is available).

.. py:method:: wait([timeout=None])

    Waits for the result value to become available, with optional wait timeout (in seconds). Default is None,
    meaning infinite timeout. If the timeout expires before the result value is available, the call
    will return ``False``. If the value has become available, it will return ``True``.

.. py:method:: then(callable [, *args, **kwargs])

    Add a callable to the call chain, to be invoked when the results become available.
    The result of the current call will be used as the first argument for the next call.
    Optional extra arguments can be provided via ``args`` and ``kwargs``.

.. py:method:: iferror(errorhandler)

    Specify the exception handler to be invoked (with the exception object as only
    argument) when asking for the result raises an exception.
    If no exception handler is set, any exception result will be silently ignored (unless
    you explicitly ask for the value). Returns self so you can easily chain other calls.


A simple piece of code showing an asynchronous method call::

    async = Pyro4.async(proxy)
    asyncresult = async.remotemethod()
    print("value available?", asyncresult.ready)
    # ...do some other stuff...
    print("resultvalue=", asyncresult.value)

.. note::

    :ref:`batched-calls` can also be executed asynchronously.
    Asynchronous calls are implemented using a background thread that waits for the results.
    Callables from the call chain are invoked sequentially in this background thread.

See the :file:`async` example for more details and example code for call chains.

Async calls for normal callables (not only for Pyro proxies)
------------------------------------------------------------
The async proxy discussed above is only available when you are dealing with Pyro proxies.
It provides a convenient syntax to call the methods on the proxy asynchronously.
For normal Python code it is sometimes useful to have a similar mechanism as well.
Pyro provides this too, see :ref:`future-functions` for more information.


.. index:: callback

Pyro Callbacks
==============
Usually there is a nice separation between a server and a client.
But with some Pyro programs it is not that simple.
It isn't weird for a Pyro object in a server somewhere to invoke a method call
on another Pyro object, that could even be running in the client program doing the initial call.
In this case the client program is a server itself as well.

These kinds of 'reverse' calls are labeled *callbacks*. You have to do a bit of
work to make them possible, because normally, a client program is not running the required
code to also act as a Pyro server to accept incoming callback calls.

In fact, you have to start a Pyro daemon and register the callback Pyro objects in it,
just as if you were writing a server program.
Keep in mind though that you probably have to run the daemon's request loop in its own
background thread. Or make heavy use of oneway method calls.
If you don't, your client program won't be able to process the callback requests because
it is by itself still waiting for results from the server.

.. index::
    single: exception in callback
    single: @Pyro4.callback
    double: decorator; callback

**Exceptions in callback objects:**
If your callback object raises an exception, Pyro will return that to the server doing the
callback. Depending on what the server does with it, you might never see the actual exception,
let alone the stack trace. This is why Pyro provides a decorator that you can use
on the methods in your callback object in the client program: ``@Pyro4.callback``.
This way, an exception in that method is not only returned to the caller, but also
logged locally in your client program, so you can see it happen including the
stack trace (if you have logging enabled)::

    import Pyro4

    class Callback(object):
    
        @Pyro4.callback
        def call(self):
            print("callback received from server!")
            return 1//0    # crash!

See the :file:`callback` example for more details and code.


.. index:: misc features

Miscellaneous features
======================
Pyro provides a few miscellaneous features when dealing with remote method calls.
They are described in this section.

.. index:: error handling

Error handling
--------------
You can just do exception handling as you would do when writing normal Python code.
However, Pyro provides a few extra features when dealing with errors that occurred in
remote objects. This subject is explained in detail its own chapter: :doc:`errors`.

See the :file:`exceptions` example for more details.

.. index:: timeouts

Timeouts
--------
Because calls on Pyro objects go over the network, you might encounter network related problems that you
don't have when using normal objects. One possible problems is some sort of network hiccup
that makes your call unresponsive because the data never arrived at the server or the response never
arrived back to the caller.

By default, Pyro waits an indefinite amount of time for the call to return. You can choose to
configure a *timeout* however. This can be done globally (for all Pyro network related operations)
by setting the timeout config item::

    Pyro4.config.COMMTIMEOUT = 1.5      # 1.5 seconds

You can also do this on a per-proxy basis by setting the timeout property on the proxy::

    proxy._pyroTimeout = 1.5    # 1.5 seconds

There is also a server setting related to oneway calls, that says if oneway method
calls should be executed in a separate thread or not. If this is set to ``False``,
they will execute in the same thread as the other method calls. This means that if the
oneway call is taking a long time to complete, the other method calls from the client may
actually stall, because they're waiting on the server to complete the oneway call that
came before them. To avoid this problem you can set this config item to True (which is the default).
This runs the oneway call in its own thread (regardless of the server type that is used)
and other calls can be processed immediately::

    Pyro4.config.ONEWAY_THREADED = True     # this is the default

See the :file:`timeout` example for more details.

Also, there is a automatic retry mechanism for timeout or connection closed (by server side),
in order to use this automatically retry::

    Pyro4.config.MAX_RETRIES = 3      # attempt to retry 3 times before raise the exception

You can also do this on a pre-proxy basis by setting the max retries property on the proxy::

    proxy._pyroMaxRetries = 3      # attempt to retry 3 times before raise the exception

Be careful to use when remote functions have a side effect (e.g.: calling twice results in error)!
See the :file:`autoretry` example for more details.

.. index::
    double: reconnecting; automatic

Automatic reconnecting
----------------------
If your client program becomes disconnected to the server (because the server crashed for instance),
Pyro will raise a :py:exc:`Pyro4.errors.ConnectionClosedError`.
You can use the automatic retry mechanism to handle this exception, see the :file:`autoretry` example for more details.
Alternatively, it is also possible to catch this and tell Pyro to attempt to reconnect to the server by calling
``_pyroReconnect()`` on the proxy (it takes an optional argument: the number of attempts
to reconnect to the daemon. By default this is almost infinite). Once successful, you can resume operations
on the proxy::

    try:
        proxy.method()
    except Pyro4.errors.ConnectionClosedError:
        # connection lost, try reconnecting
        obj._pyroReconnect()

This will only work if you take a few precautions in the server. Most importantly, if it crashed and comes
up again, it needs to publish its Pyro objects with the exact same URI as before (object id, hostname, daemon
port number).

See the :file:`autoreconnect` example for more details and some suggestions on how to do this.

The ``_pyroReconnect()`` method can also be used to force a newly created proxy to connect immediately,
rather than on first use.


.. index:: proxy sharing

Proxy sharing
-------------
Due to internal locking you can freely share proxies among threads.
The lock makes sure that only a single thread is actually using the proxy's
communication channel at all times.
This can be convenient *but* it may not be the best way to approach things. The lock essentially
prevents parallelism. If you want calls to go in parallel, give each thread its own proxy.

Here are a couple of suggestions on how to make copies of a proxy:

#. use the :py:mod:`copy` module, ``proxy2 = copy.copy(proxy)``
#. create a new proxy from the uri of the old one: ``proxy2 = Pyro4.Proxy(proxy._pyroUri)``
#. simply create a proxy in the thread itself (pass the uri to the thread instead of a proxy)

See the :file:`proxysharing` example for more details.


.. index::
    double: Daemon; Metadata

.. _metadata:

Metadata from the daemon
------------------------
A proxy will obtain some meta-data from the daemon about the object it connects to.
It does that by calling the (public) :py:meth:`Pyro4.core.DaemonObject.get_metadata` daemon-method as soon as
it connects to the daemon [1]_. A bunch of information about the object (or rather, its class) is returned:
what methods and attributes are defined, and which of the methods are to be called as one-way.
This information is used to properly execute one-way calls, and to do client-side validation of calls on the proxy
(for instance to see if a method or attribute is actually available, without having to do a round-trip to the server).
Also this enables a properly working ``hasattr`` on the proxy, and efficient and specific error messages
if you try to access a method or attribute that is not defined or not exposed on the Pyro object.
Lastly the direct access to attributes on the remote object is also made possible, because the proxy knows about what
attributes are available.

You can disable this mechanism by setting the ``METADATA`` config item to ``False`` (it's ``True`` by default).
This will improve efficiency when connecting a proxy (because no meta data roundtrip to the server has to be done)
but your proxy will not know about the features of the Pyro object as mentioned above.
Disabling it also allows you to connect to older Pyro versions that don't implement the metadata protocol yet (4.26 and older).
You can tell if you need to do this if you're getting errors in your proxy saying that 'DaemonObject' has no attribute 'get_metdata'.
Either upgrade the Pyro version of the server, or set the ``METDATA`` config item to False in your client code.


.. rubric:: Footnotes

.. [1] Actually this is optimized in recent Pyro versions. Pyro will now immediately
    return the object metadata as part of the response message from the initial connection handshake.
    This avoids a separate remote call to get_metadata.
