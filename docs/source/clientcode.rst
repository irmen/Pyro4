*******************************
Clients: Calling remote objects
*******************************

This chapter explains how you write code that calls remote objects.
Often, a program that calls methods on a Pyro object is called a *client* program.
(The program that provides the object and actually runs the methods, is the *server*.
Both roles can be mixed in a single program.)

Make sure you are familiar with Pyro's :ref:`keyconcepts` before reading on.

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
    So this means you can write::

        uri_string = "PYRONAME:musicserver"
        # or Pyro4.URI("PYRONAME:musicserver") for an URI object

    You can use this URI everywhere you would normally use a normal uri (using ``PYRO``).
    Everytime Pyro encounters the ``PYRONAME`` uri it will use the name server automatically
    to look up the object for you. [#pyroname]_

.. [#pyroname] this is not very efficient if it occurs often. Have a look at the :doc:`tipstricks`
   chapter for some hints about this.


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
        print "Currently playing:", musicserver.current_song()
    except MediaServerException:
        print "Couldn't select playlist or start playing"

For normal usage, there's not a single line of Pyro specific code once you have a proxy!

Proxies, connections, threads and cleaning up
=============================================
Here are some rules:

* Every single Proxy object will have its own socket connection to the daemon.
* You can share Proxy objects among threads, it will re-use the same socket connection.
* Usually every connection in the daemon has its own processing thread there, but for more details see the :doc:`servercode` chapter.
* The connection will remain active for the lifetime of the proxy object.
* You can free resources by manually closing the proxy connection if you don't need it anymore.
  This can be done in two ways:

  1. calling ``_pyroRelease()`` on the proxy.
  2. using the proxy as a context manager in a ``with`` statement.
     This ensures that when you're done with it, or an error occurs (inside the with-block),
     the connection is released::

        with Pyro4.Proxy(".....") as obj:
            obj.method()

  .. note::
    You can still use the proxy object when it is disconnected: Pyro will reconnect it as soon as it's needed again.


Oneway calls
============
Normal method calls always block until the response is returned. This can be a normal return value, ``None``,
or an error in the form of a raised exception.

If you know that some methods never return any response or you are simply not interested in it (including
exceptions!) you can tell Pyro that certain methods of a proxy object are *one-way* calls::

    proxy._pyroOneway.add("someMethod")
    proxy._pyroOneway.update(["otherMethod", "processStuff"])

the :py:attr:`Pyro4.core.Proxy._pyroOneway` property is a set containing the names of the methods that
should be called as one-way (by default it is an empty set). For these methods, Pyro will not wait for a response
from the remote object. This means that your client program continues to
work, while the remote object is still busy processing the method call.
The return value of these calls is always ``None``. You can't tell if the method call
was successful, or if the method even exists on the remote object, because errors won't be returned either!

See the :file:`oneway` example for more details.

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

#. You create a batch proxy wrapper object for the proxy object.
#. Call all the methods you would normally call on the regular proxy, but use the batch proxy wrapper object instead.
#. Call the batch proxy object itself to obtain the generator with the results.

You create a batch proxy wrapper using this: ``batch = Pyro4.batch(proxy)`` or this (equivalent): ``batch = proxy._pyroBatch()``.
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
        print result   # process result in order of calls...

**Oneway batch**::

    results = batch(oneway=True)
    # results==None

**Asynchronous batch**

The result value of an asynchronous batch call is a special object. See :ref:`async-calls` for more details about it.
This is some simple code doing an asynchronous batch::

    results = batch(async=True)
    # do some stuff... until you're ready and require the results of the async batch:
    for result in results.value:
        print result    # process the results


See the :file:`batchedcalls` example for more details.

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

You create an async proxy wrapper using this: ``async = Pyro4.async(proxy)`` or this (equivalent): ``async = proxy._pyroAsync()``.
Every remote method call you make on the async proxy wrapper, returns a
:py:class:`Pyro4.core.FutureResult` object immediately.
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

A simple piece of code showing an asynchronous method call::

    async = Pyro4.async(proxy)
    asyncresult = async.remotemethod()
    print "value available?", asyncresult.ready
    # ...do some other stuff...
    print "resultvalue=", asyncresult.value

.. note::

    :ref:`batched-calls` can also be executed asynchronously.
    Asynchronous calls are implemented using a background thread that waits for the results.
    Callables from the call chain are invoked sequentially in this background thread.

See the :file:`async` example for more details and example code for call chains.

Async calls for normal callables (not only for Pyro proxies)
------------------------------------------------------------
The async proxy wrapper discussed above is only available when you are dealing with Pyro proxies.
It provides a convenient syntax to call the methods on the proxy asynchronously.
For normal Python code it is sometimes useful to have a similar mechanism as well.
Pyro provides this too, see :ref:`future-functions` for more information.


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

**Exceptions in callback objects:**
If your callback object raises an exception, Pyro will return that to the server doing the
callback. Depending on what that does with it, you might never see the actual exception,
let alone the stack trace. This is why Pyro provides a decorator that you can use
on the methods in your callback object in the client program: ``@Pyro4.core.callback``
(also available for convenience as ``@Pyro4.callback``).
This way, an exception in that method is not only returned to the caller, but also
raised again locally in your client program, so you can see it happen including the
stack trace::

    class Callback(object):
    
        @Pyro4.callback
        def call(self):
            print("callback received from server!")
            return 1//0    # crash away

See the :file:`callback` example for more details and code.

Miscellaneous features
======================
Pyro provides a few miscellaneous features when dealing with remote method calls.
They are described in this section.

Error handling
--------------
You can just do exception handling as you would do when writing normal Python code.
However, Pyro provides a few extra features when dealing with errors that occurred in
remote objects. This subject is explained in detail its own chapter: :doc:`errors`.

See the :file:`exceptions` example for more details.

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
they will execute in

    Pyro4.config.ONEWAY_THREADED = True     # this is the default

See the :file:`timeout` example for more details.

Automatic reconnecting
----------------------
If your client program becomes disconnected to the server (because the server crashed for instance),
Pyro will raise a :py:exc:`Pyro4.errors.ConnectionClosedError`.
It is possible to catch this and tell Pyro to attempt to reconnect to the server by calling
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
