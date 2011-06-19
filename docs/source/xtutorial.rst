Tutorial
********

This tutorial will explain a couple of basic Pyro concepts,
a little bit about the name server, and you'll learn to write a simple Pyro application.
You'll do this by writing a warehouse system and a stockmarket simulator,
that demonstrate some key Pyro techniques.

Warm-up
=======

Before proceeding, you should install Pyro if you haven't done so. For instructions about that, see :ref:`config-install`.

In this tutorial, you will use Pyro's default configuration settings, so once Pyro is installed, you're all set!
All you need is a text editor and a couple of console windows.

.. note::
    The code of the two tutorial 'projects' is included in the Pyro source archive.
    Just installing Pyro won't provide this.
    If you don't want to type all the code, you should extract the Pyro source archive 
    (:file:`Pyro4-X.Y.tar.gz`) somewhere. You will then have an :file:`examples` directory
    that contains a truckload of examples, including the two tutorial projects we will
    be creating later in this tutorial, :file:`warehouse` and :file:`stockquotes`.
    (There is more in there as well: the :file:`tests` directory contains the test suite
    with all the unittests for Pyro's code base.)


Pyro concepts and tools
=======================

Pyro enables code to call methods on objects even if that object is running on a remote machine::

    +----------+                         +----------+
    | server A |                         | server B |
    |          |       < network >       |          |
    | Python   |                         |   Python |
    | OBJECT ----------foo.invoke()--------> OBJECT |
    |          |                         |     foo  |
    +----------+                         +----------+

Pyro is mainly used as a library in your code but it also has several supporting command line tools [#commandline]_.
We won't explain every one of them here as you will only need the "name server" for this tutorial.
The name server is a utility that provides a phonebook for Pyro applications: you use it to look up a "number" by a "name". 
The name in Pyro's case is the logical name of a remote object. The number is the exact location where Pyro can contact the object.
We will see later what both actually look like, and why having a name server can be useful.

.. [#commandline] Actually there are no scripts or command files included with Pyro right now.
  The command line tools are invoked by starting their package directly using the :kbd:`-m` argument 
  of the Python interpreter.

Starting a name server
^^^^^^^^^^^^^^^^^^^^^^

We will be needing the name server later, and it shows a few basic Pyro concepts,
so let us begin by explaining a little about it.
Open a console window and execute the following command to start a name server:

:command:`python -Wignore -m Pyro4.naming`

The :kbd:`-Wignore` is added to suppress a Pyro warning that we're not interested in right now.
The name server will start and it prints something like::

    Not starting broadcast server for localhost.
    NS running on localhost:9090 (127.0.0.1)
    URI = PYRO:Pyro.NameServer@localhost:9090

.. sidebar:: Localhost

   By default, Pyro uses *localhost* to run stuff on, so you can't by mistake expose your system to the outside world.
   You'll need to tell Pyro explicitly to use something else than *localhost*. But it is fine for the tutorial,
   so we leave it as it is.

The name server has started and is listening on *localhost port 9090*.

It also printed an :abbr:`URI (unique resource identifier)`. This is what Pyro uses to uniquely identify every object.
(similar to what a web page URL is to documents on the web).
It is read like this: "PYRO:" + object name + "@" + server name + port number.

The name server can be stopped with a :kbd:`control-c`, or on Windows, with :kbd:`ctrl-break`. But let it run 
in the background for the rest of this tutorial.


Interacting with the name server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There's another command line tool that let you interact with the name server: "nsc" (name server controltool).
You can use it, amongst other things, to see what all known registered objects in the naming server are.
Let's do that right now. Type:

:command:`python -Wignore -m Pyro4.nsc list`

(the :kbd:`-Wignore` again is to suppress a warning) and it will print something like this::

    --------START LIST
    Pyro.NameServer --> PYRO:Pyro.NameServer@localhost:9090
    --------END LIST

The only object that is currently registered, is the name server itself! (Yes, the name server is a Pyro object
itself. Pyro and the "nsc" tool are using Pyro to talk to it).

.. note:: As you can see, the name ``Pyro.NameServer`` is registered to point to the URI that we saw earlier.
   This is mainly for completeness sake, and is not often used, because there are different ways to get
   to talk to the name server (see below).

This is cool, but there's a little detail left unexplained: *How did the nsc tool know where the name server was?*
Pyro has a couple of tactics to locate a name server.  The nsc tool uses them too:
Pyro uses a network broadcast to see if there's a name server available somewhere (the name server contains
a broadcast responder that will respond "Yeah hi I'm here").  So in many cases you won't have to configure anything
to be able to discover the name server. If nobody answers though, Pyro tries the configured default or custom location.
If still nobody answers it prints a sad message and exits.
However if it found the name server, it is then possible to talk to it and get the location of any other registered object.
. This means that you won't have to hardcode any object locations in your code,
and that the code is capable of dynamically discovering everything at runtime.

*But enough of that.* We need to start looking at how to actually write some code ourselves that uses Pyro!

Building a Warehouse
====================

.. hint:: The code of this part of the tutorial can be found in the :file:`examples/warehouse` directory.

You'll build build a simple ware house that stores items. 
The idea is that there is one big warehouse that everyone can store items
in, and retrieve other items from (if they're in the warehouse).

phase 1: simple prototype
^^^^^^^^^^^^^^^^^^^^^^^^^
*Simple prototype code where everything is running in a single process.
visit.py creates the warehouse and two visitors.
This code is fully operational but contains no Pyro code at all and
shows what the system is going to look like later on.*

phase 2: first Pyro version
^^^^^^^^^^^^^^^^^^^^^^^^^^^
*Pyro is now used to make the warehouse a standalone component.
You can still visit it ofcourse. visit.py does need the URI of the
warehouse however. (It is printed as soon as the warehouse is started)
The code of the Warehouse and the Person classes is unchanged.*

phase 3: final Pyro version
^^^^^^^^^^^^^^^^^^^^^^^^^^^
*Phase 2 works fine but is a bit cumbersome because you need to copy-paste
the warehouse URI to be able to visit it.
Phase 3 simplifies things a bit by using the Pyro name server.
Also, it uses the Pyro excepthook to print a nicer exception message
if anything goes wrong. (Try taking something from the warehouse that is not present!)
The code of the Warehouse and the Person classes is still unchanged.*


Building a Stockmarket simulator
================================

.. hint:: The code of this part of the tutorial can be found in the :file:`examples/stockquotes` directory.

You'll build a simple stock quote system.
The idea is that we have multiple stock markets producing stock symbol
quotes. There is an aggregator that combines the quotes from all stock
markets. Finally there are multiple viewers that can register themselves
by the aggregator and let it know what stock symbols they're interested in.
The viewers will then receive near-real-time stock quote updates for the
symbols they selected.  (Everything is fictional, ofcourse)::

    Stockmarket  ->-----\                /----> Viewer
    Stockmarket  ->------>  Aggregator ->-----> Viewer
    Stockmarket  ->-----/                \----> Viewer


phase 1: simple prototype
^^^^^^^^^^^^^^^^^^^^^^^^^
*Simple prototype code where everything is running in a single process.
Main.py creates all object, connects them together, and contains a loop
that drives the stockmarket quote generation.
This code is fully operational but contains no Pyro code at all and
shows what the system is going to look like later on.*


phase 2: separation
^^^^^^^^^^^^^^^^^^^
*Still no Pyro code, but the components are now more autonomous.
They each have a main function that starts up the component and connects
it to the other component(s). As the Stockmarket is the source of the
data, it now contains a thread that produces stock quote changes.
Main.py now only starts the various components and then sits to wait
for an exit signal.
While this phase still doesn't use Pyro at all, the structure of the
code and the components are very close to what we want to achieve
in the end where everything is fully distributed.*

phase 3: Pyro version
^^^^^^^^^^^^^^^^^^^^^
*The components are now fully distributed and we used Pyro to make them
talk to each other. There is no main.py anymore because you have to start
every component by itself: (in seperate console windows for instance)*

- start a Pyro name server (python -m Pyro4.naming)
- start the stockmarket
- start the aggregator
- start one or more of the viewers.
