Writing clients (@todo)
***********************

This chapter explains how you go about writing 'client' programs.
A client is a program that calls methods on a Pyro object.
(The program that provides the object and actually runs the methods, is the server.
Note that they can be mixed.)

Make sure you know what a Proxy, URI, Pyro object and a Pyro Name Server is.
See :ref:`keyconcepts` for a quick introduction.

.. note::
  This chapter still needs to be expanded more


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

Advanced features
=================
Pyro provides a few extra features when dealing with remote method calls. This paragraph talks about them.

Error handling
--------------
This subject is explained in its own chapter, :doc:`errors`.

Timeouts
--------
@todo

Oneway calls
------------
@todo

Automatic reconnecting
----------------------
@todo

Batched calls
-------------
@todo

Asynchronous calls
------------------
@todo

Proxy sharing
-------------
@todo
