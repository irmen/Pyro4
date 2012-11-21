*****************
Intro and Example
*****************

.. image:: _static/pyro-large.png
  :align: center

This chapter contains a little overview of Pyro's features and a simple example to show how it looks like.

About Pyro: feature overview
============================

Pyro is a library that enables you to build applications in which
objects can talk to each other over the network, with minimal programming effort.
You can just use normal Python method calls, with almost every possible parameter
and return value type, and Pyro takes care of locating the right object on the right
computer to execute the method. It is designed to be very easy to use, and to
generally stay out of your way. But it also provides a set of powerful features that
enables you to build distributed applications rapidly and effortlessly.
Pyro is written in **100% pure Python** and therefore runs on many platforms and Python versions,
**including Python 3.x**.

Here's a quick overview of Pyro's features:

- written in 100% Python so extremely portable.
- support for all Python data types that are pickleable.
- runs on normal Python 2.x, Python **3.x**, IronPython, Jython, Pypy.
- works between systems on different architectures and operating systems (64-bit, 32-bit, Intel, PowerPC...)
- designed to be very easy to use and get out of your way as much as possible.
- name server that keeps track of your object's actual locations so you can move them around transparently.
- support for automatic reconnection to servers in case of interruptions.
- automatic proxy-ing of Pyro objects which means you can return references to remote objects just as if it were normal objects.
- one-way invocations for enhanced performance.
- batched invocations for greatly enhanced performance of many calls on the same object.
- you can define timeouts on network communications to prevent a call blocking forever if there's something wrong.
- asynchronous invocations if you want to get the results 'at some later moment in time'. Pyro will take care of gathering the result values in the background.
- remote exceptions will be raised in the caller, as if they were local. You can extract detailed remote traceback information.
- stable network communication code that works reliably on many platforms.
- possibility to use Pyro's own event loop, or integrate it into your own (or third party) event loop.
- many simple examples included to show various features and techniques.
- large amount of unit tests and high test coverage.
- built upon more than 10 years of existing Pyro history.
- can use IPv4 and Unix domain sockets (IPv6 is not yet supported but it is being developed)

.. warning::
    Pyro uses the :py:mod:`pickle` module to serialize objects and sends them over the network.
    It is well known that using :py:mod:`pickle` for this purpose is a security risk
    (The main problem is that allowing your program to unpickle arbitrary data can cause
    arbitrary code execution and may wreck or compromise your system).
    However, Pyro has some security measures in place to deal with this.
    They are described in the :doc:`security` chapter. It is strongly advised to read it.


Pyro's history
^^^^^^^^^^^^^^
Pyro was started in 1998, more than ten years ago, when remote method invocation technology such as Java's RMI
and CORBA were quite popular. I wanted something like that in Python and there was nothing available, so I decided
to write my own. Over the years it slowly gained features till it reached version 3.10 or so.
At that point it was clear that the code base had become quite ancient and couldn't reliably support any new features,
so Pyro4 was born in early 2010, written from scratch. After a couple of versions Pyro4 became stable enough to be considered
the new 'main' Pyro version to be preferred over Pyro 3.x (unless you have specific requirements that force you
to stick with Pyro3). See :doc:`upgrading` for more information on the different versions and how to upgrade old code to Pyro4.

``Pyro`` is the package name of the older, 3.x version of Pyro.
``Pyro4`` is the package name of the new, current version. Its API and behavior is similar to Pyro 3.x but it is not
backwards compatible. So to avoid conflicts, this new version has a different package name.

If you're interested in the old version, here is `its homepage <http://irmen.home.xs4all.nl/pyro3/>`_
and it is also `available on PyPi <http://pypi.python.org/pypi/Pyro/>`_.

What can you use it for?
========================

Essentially, Pyro can be used to distribute various kinds of resources or responsibilities:
computational (hardware) resources (cpu, storage, printers),
informational resources (data, privileged information)
and business logic (departments, domains).

An example would be a high performance compute cluster with a large storage system attached to it.
Usually such a beast is not be accessible directly, rather, smaller systems connect to it and
feed it with jobs that need to run on the big cluster. Later, they collect the results.
Pyro could be used to expose the available resources on the cluster to other computers.
Their client software connects to the cluster and calls the Python program there to perform its
heavy duty work, and collect the results (either directly from a method call return value,
or perhaps via asynchronous callbacks).

Remote controlling resources or other programs is a nice application as well.
For instance, you could write a simple
remote controller for your media server that is running on a machine somewhere in a closet.
A simple remote control client program could be used to instruct the media server
to play music, switch playlists, etc. 

Another example is the use of Pyro to implement a form of `privilege separation <http://en.wikipedia.org/wiki/Privilege_separation>`_.
There is a small component running with higher privileges, but just able to execute the few tasks (and nothing else)
that require those higher privileges. That component could expose one or more Pyro objects
that represent the privileged information or logic.
Other programs running with normal privileges can talk to those Pyro objects to
perform those specific tasks with higher privileges in a controlled manner.

On a lower level Pyro is just a form of inter-process communication. So everywhere you would otherwise have
used a more primitive form of IPC (such as plain TCP/IP sockets) between Python components, you could consider to use
Pyro instead.

Have a look at the :file:`examples` directory in the source archive, perhaps one of the many example
programs in there gives even more inspiration of possibilities.

Simple Example
==============

This example will show you in a nutshell what it's like to use Pyro in your programs.
A much more extensive introduction is found in the :doc:`tutorials`.

We're going to write a simple greeting service that will return a personalized greeting message to its callers.

Let's start by just writing it in normal Python first (create two files)::

    # save this as greeting.py
    class GreetingMaker(object):
        def get_fortune(self, name):
            return "Hello, {0}. Here is your fortune message:\n" \
                   "Behold the warranty -- the bold print giveth and the fine print taketh away.".format(name)

::

    # save this as client.py
    import greeting
    name=raw_input("What is your name? ")
    greeting_maker=greeting.GreetingMaker()
    print greeting_maker.get_fortune(name)

If you then run it with :command:`python client.py` a session looks like this::

    $ python client.py
    What is your name? Irmen
    Hello, Irmen. Here is your fortune message:
    Behold the warranty -- the bold print giveth and the fine print taketh away.

Right that works like a charm but we are now going to use Pyro to make this into a greeting server that you
can access easily from anywhere. The :file:`greeting.py` is going to be our server. We'll need to import the
Pyro package, start up a Pyro daemon (server) and connect a GreetingMaker object to it::

    # saved as greeting.py
    import Pyro4

    class GreetingMaker(object):
        def get_fortune(self, name):
            return "Hello, {0}. Here is your fortune message:\n" \
                   "Behold the warranty -- the bold print giveth and the fine print taketh away.".format(name)

    greeting_maker=GreetingMaker()

    daemon=Pyro4.Daemon()                 # make a Pyro daemon
    uri=daemon.register(greeting_maker)   # register the greeting object as a Pyro object

    print "Ready. Object uri =", uri      # print the uri so we can use it in the client later
    daemon.requestLoop()                  # start the event loop of the server to wait for calls

And now all that is left is a tiny piece of code that invokes the server from somewhere::

    # saved as client.py
    import Pyro4

    uri=raw_input("What is the Pyro uri of the greeting object? ").strip()
    name=raw_input("What is your name? ").strip()

    greeting_maker=Pyro4.Proxy(uri)          # get a Pyro proxy to the greeting object
    print greeting_maker.get_fortune(name)   # call method normally

Open a console window and start the greeting server::

    $ python greeting.py
    Ready. Object uri = PYRO:obj_edb9e53007ce4713b371d0dc6a177955@localhost:51681

(The uri is randomly generated) Open another console window and start the client program::

    $ python client.py
    What is the Pyro uri of the greeting object?  <<paste the printed uri from the server>>
    What is your name?  <<type your name, Irmen in this example>>
    Hello, Irmen. Here is your fortune message:
    Behold the warranty -- the bold print giveth and the fine print taketh away.

This covers the most basic use of Pyro! As you can see, all there is to it is starting a daemon,
registering one or more objects with it, and getting a proxy to these objects to call methods on
as if it was the actual object itself.

With a name server
^^^^^^^^^^^^^^^^^^
While the example above works, it could become tiresome to work with object uris like that.
There's already a big issue, *how is the client supposed to get the uri, if we're not copy-pasting it?*
Thankfully Pyro provides a *name server* that works like an automatic phone book.
You can name your objects using logical names and use the name server to search for the
corresponding uri.

We'll have to modify a few lines in :file:`greeting.py` to make it register the object in the name server::

    # saved as greeting.py
    import Pyro4

    class GreetingMaker(object):
        def get_fortune(self, name):
            return "Hello, {0}. Here is your fortune message:\n" \
                   "Tomorrow's lucky number is 12345678.".format(name)

    greeting_maker=GreetingMaker()

    daemon=Pyro4.Daemon()                 # make a Pyro daemon
    ns=Pyro4.locateNS()                   # find the name server
    uri=daemon.register(greeting_maker)   # register the greeting object as a Pyro object
    ns.register("example.greeting", uri)  # register the object with a name in the name server

    print "Ready."
    daemon.requestLoop()                  # start the event loop of the server to wait for calls

The :file:`client.py` is actually simpler now because we can use the name server to find the object::

    # saved as client.py
    import Pyro4

    name=raw_input("What is your name? ").strip()

    greeting_maker=Pyro4.Proxy("PYRONAME:example.greeting")    # use name server object lookup uri shortcut
    print greeting_maker.get_fortune(name)

The program now needs a Pyro name server that is running. You can start one by typing the
following command: :command:`python -m Pyro4.naming` in a separate console window
(usually there is just *one* name server running in your network).
After that, start the server and client as before.
There's no need to copy-paste the object uri in the client any longer, it will 'discover'
the server automatically, based on the object name (:kbd:`example.greeting`).
If you want you can check that this name is indeed known in the name server, by typing
the command :command:`python -m Pyro4.nsc list`, which will produce::

    $ python -m Pyro4.nsc list
    --------START LIST
    Pyro.NameServer --> PYRO:Pyro.NameServer@localhost:9090
    example.greeting --> PYRO:obj_663a31d2dde54b00bfe52ec2557d4f4f@localhost:51707
    --------END LIST

(Once again the uri for our object will be random)
This concludes this simple Pyro example.

.. note::
 In the source archive there is a directory :file:`examples` that contains a truckload
 of example programs that show the various features of Pyro. If you're interested in them
 (it is highly recommended to be so!) you will have to download the Pyro distribution archive.
 Installing Pyro only provides the library modules. For more information, see :doc:`config`.

Other means of creating connections
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The example above showed two of the basic ways to set up connections between your client and server code.
There are various other options, have a look at the client code details: :ref:`object-discovery`
and the server code details: :ref:`publish-objects`. The use of the name server is optional, see
:ref:`name-server` for details.


Performance
===========
Pyro4 is really fast at what it does. This is due to its low overhead and use of native Python serialization (pickle).
Here are some measurements done between two processes running on a Core 2 Duo 3Ghz, Windows 7 machine.

:benchmark/connections.py:
    | 2000 connections in 1.139 sec = 1756 conn/sec
    | 2000 new proxy calls in 1.451 sec = 1378 calls/sec
    | 10000 calls in 1.058 sec = 9452 calls/sec

:benchmark/client.py:
    | total time 1.761 seconds
    | total method calls: 15000
    | avg. time per method call: 0.117 msec (8517/sec)

:hugetransfer/client.py:
    | It took 0.48 seconds to transfer 51269 kilobyte.
    | That is 106148 k/sec. = 103.7 mb/sec.

:batchedcalls/client.py:
    | Batched remote calls...
    | processing the results...
    | total time taken 0.29 seconds (136500 calls/sec)
    | batched calls were 14.1 times faster than normal remote calls

    | Oneway batched remote calls...
    | executing batch, there will be no result values. Check server to see printed messages...
    | total time taken 0.19 seconds (215000 calls/sec)
    | oneway batched calls were 22.2 times faster than normal remote calls
