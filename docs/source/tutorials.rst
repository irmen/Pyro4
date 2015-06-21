.. include:: <isonum.txt>
.. index:: tutorial

********
Tutorial
********

This tutorial will explain a couple of basic Pyro concepts,
a little bit about the name server, and you'll learn to write a simple Pyro application.
You'll do this by writing a warehouse system and a stock market simulator,
that demonstrate some key Pyro techniques.

Warm-up
=======

Before proceeding, you should install Pyro if you haven't done so. For instructions about that, see :doc:`install`.

In this tutorial, you will use Pyro's default configuration settings, so once Pyro is installed, you're all set!
All you need is a text editor and a couple of console windows.
During the tutorial, you are supposed to run everything on a single machine.
This avoids initial networking complexity.

.. note::
    For security reasons, Pyro runs stuff on localhost by default.
    If you want to access things from different machines, you'll have to tell Pyro
    to do that explicitly.
    At the end is a small paragraph :ref:`not-localhost` that tells you
    how you can run the various components on different machines.

.. note::
    The code of the two tutorial 'projects' is included in the Pyro source archive.
    Just installing Pyro won't provide this.
    If you don't want to type all the code, you should extract the Pyro source archive
    (:file:`Pyro4-X.Y.tar.gz`) somewhere. You will then have an :file:`examples` directory
    that contains a truckload of examples, including the two tutorial projects we will
    be creating later in this tutorial, :file:`warehouse` and :file:`stockquotes`.
    (There is more in there as well: the :file:`tests` directory contains the test suite
    with all the unittests for Pyro's code base.)


.. index::
    double: tutorial; concepts and tools

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

.. [#commandline] Actually there are no scripts or command files included with Pyro right now.
  The :ref:`command-line` are invoked by starting their package directly using the :kbd:`-m` argument
  of the Python interpreter.

.. _keyconcepts:

Key concepts
^^^^^^^^^^^^
Here are a couple of key concepts you encounter when using Pyro:

Proxy
    A proxy is a substitute object for "the real thing".
    It intercepts the method calls you would normally do on an object as if it was the actual object.
    Pyro then performs some magic to transfer the call to the computer that contains the *real* object,
    where the actual method call is done, and the results are returned to the caller.
    This means the calling code doesn't have to know if it's dealing with a normal or a remote object,
    because the code is identical.
    The class implementing Pyro proxies is ``Pyro4.Proxy`` (shortcut for :class:`Pyro4.core.Proxy`)

:abbr:`URI (Unique resource identifier)`
    This is what Pyro uses to identify every object.
    (similar to what a web page URL is to point to the different documents on the web).
    Its string form is like this: "PYRO:" + object name + "@" + server name + port number.
    There are a few other forms it can take as well.
    You can write the protocol in lowercase too if you want ("pyro:") but it will
    automatically be converted to uppercase internally.
    The class implementing Pyro uris is ``Pyro4.URI`` (shortcut for :class:`Pyro4.core.URI`)

Pyro object
    This is a normal Python object but it is registered with Pyro so that you can access it remotely.
    Pyro objects are written just as any other object but the fact that Pyro knows something about
    them makes them special, in the way that you can call methods on them from other programs.
    A class can also be a Pyro object, but then you will also have to tell Pyro about how it
    should create actual objects from that class when handling remote calls.

Pyro daemon (server)
    This is the part of Pyro that listens for remote method calls, dispatches them
    to the appropriate actual objects, and returns the results to the caller.
    All Pyro objects are registered in one or more daemons.

Pyro name server
    The name server is a utility that provides a phone book for Pyro applications: you use it to look up a "number" by a "name".
    The name in Pyro's case is the logical name of a remote object. The number is the exact location where Pyro can contact the object.
    Usually there is just *one* name server running in your network.

Serialization
    This is the process of transforming objects into streams of bytes that can be transported
    over the network. The receiver deserializes them back into actual objects. Pyro needs to do
    this with all the data that is passed as arguments to remote method calls, and their response
    data. Not all objects can be serialized, so it is possible that passing a certain object to
    Pyro won't work even though a normal method call would accept it just fine.

Configuration
    Pyro can be configured in a lot of ways. Using environment variables (they're prefixed with ``PYRO_``)
    or by setting config items in your code. See the configuration chapter for more details.
    The default configuration should be ok for most situations though, so you many never have to touch
    any of these options at all!


Starting a name server
^^^^^^^^^^^^^^^^^^^^^^

While the use of the Pyro name server is optional, we will use it in this tutorial.
It also shows a few basic Pyro concepts, so let us begin by explaining a little about it.
Open a console window and execute the following command to start a name server:

:command:`python -m Pyro4.naming` (or simply: :command:`pyro4-ns`)

The name server will start and it prints something like::

    Not starting broadcast server for localhost.
    NS running on localhost:9090 (127.0.0.1)
    URI = PYRO:Pyro.NameServer@localhost:9090

.. sidebar:: Localhost

   By default, Pyro uses *localhost* to run stuff on, so you can't by mistake expose your system to the outside world.
   You'll need to tell Pyro explicitly to use something else than *localhost*. But it is fine for the tutorial,
   so we leave it as it is.

The name server has started and is listening on *localhost port 9090*.

It also printed an :abbr:`URI (unique resource identifier)`. Remember that this is
what Pyro uses to identify every object.

The name server can be stopped with a :kbd:`control-c`, or on Windows, with :kbd:`ctrl-break`. But let it run
in the background for the rest of this tutorial.


Interacting with the name server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There's another command line tool that let you interact with the name server: "nsc" (name server control tool).
You can use it, amongst other things, to see what all known registered objects in the naming server are.
Let's do that right now. Type:

:command:`python -m Pyro4.nsc list` (or simply: :command:`pyro4-nsc list`)

and it will print something like this::

    --------START LIST
    Pyro.NameServer --> PYRO:Pyro.NameServer@localhost:9090
    --------END LIST

The only object that is currently registered, is the name server itself! (Yes, the name server is a Pyro object
itself. Pyro and the "nsc" tool are using Pyro to talk to it).

.. note:: As you can see, the name ``Pyro.NameServer`` is registered to point to the URI that we saw earlier.
   This is mainly for completeness sake, and is not often used, because there are different ways to get
   to talk to the name server (see below).

.. sidebar:: The NameServer object

  The name server itself is a normal Pyro object which means the 'nsc' tool, and any other code that talks to it,
  is just using normal Pyro methods. The only "trickery" that makes it a bit different from other Pyro servers
  is perhaps the broadcast responder, and the two command line tools to interact with it (``Pyro4.naming`` and
  ``Pyro4.nsc``)

This is cool, but there's a little detail left unexplained: *How did the nsc tool know where the name server was?*
Pyro has a couple of tactics to locate a name server.  The nsc tool uses them too:
Pyro uses a network broadcast to see if there's a name server available somewhere (the name server contains
a broadcast responder that will respond "Yeah hi I'm here").  So in many cases you won't have to configure anything
to be able to discover the name server. If nobody answers though, Pyro tries the configured default or custom location.
If still nobody answers it prints a sad message and exits.
However if it found the name server, it is then possible to talk to it and get the location of any other registered object.
. This means that you won't have to hard code any object locations in your code,
and that the code is capable of dynamically discovering everything at runtime.

*But enough of that.* We need to start looking at how to actually write some code ourselves that uses Pyro!

.. index::
    double: tutorial; warehouse example

Building a Warehouse
====================

.. hint:: All code of this part of the tutorial can be found in the :file:`examples/warehouse` directory.

You'll build build a simple warehouse that stores items, and that everyone can visit.
Visitors can store items and retrieve other items from the warehouse (if they've been stored there).

In this tutorial you'll first write a normal Python program that more or less implements the complete warehouse system,
but in vanilla Python code. After that you'll add Pyro support to it, to make it a distributed warehouse system,
where you can visit the central warehouse from many different computers.

phase 1: a simple prototype
^^^^^^^^^^^^^^^^^^^^^^^^^^^
To start with, write the vanilla Python code for the warehouse and its visitors.
This prototype is fully working but everything is running in a single process. It contains no Pyro
code at all, but shows what the system is going to look like later on.

The ``Warehouse`` object simply stores an array of items which we can query, and allows for a person
to take an item or to store an item. Here is the code (:file:`warehouse.py`)::

    from __future__ import print_function

    class Warehouse(object):
        def __init__(self):
            self.contents = ["chair", "bike", "flashlight", "laptop", "couch"]

        def list_contents(self):
            return self.contents

        def take(self, name, item):
            self.contents.remove(item)
            print("{0} took the {1}.".format(name, item))

        def store(self, name, item):
            self.contents.append(item)
            print("{0} stored the {1}.".format(name, item))


Then there is a ``Person`` that can visit the warehouse. The person has a name and deposit and retrieve actions
on a particular warehouse. Here is the code (:file:`person.py`)::

    from __future__ import print_function
    import sys

    if sys.version_info < (3, 0):
        input = raw_input


    class Person(object):
        def __init__(self, name):
            self.name = name
			
        def visit(self, warehouse):
            print("This is {0}.".format(self.name))
            self.deposit(warehouse)
            self.retrieve(warehouse)
            print("Thank you, come again!")
			
        def deposit(self, warehouse):
            print("The warehouse contains:", warehouse.list_contents())
            item = input("Type a thing you want to store (or empty): ").strip()
            if item:
                warehouse.store(self.name, item)
				
        def retrieve(self, warehouse):
            print("The warehouse contains:", warehouse.list_contents())
            item = input("Type something you want to take (or empty): ").strip()
            if item:
                warehouse.take(self.name, item)


Finally you need a small script that actually runs the code. It creates the warehouse and two visitors, and
makes the visitors perform their actions in the warehouse. Here is the code (:file:`visit.py`)::

    # This is the code that runs this example.
    from warehouse import Warehouse
    from person import Person

    warehouse = Warehouse()
    janet = Person("Janet")
    henry = Person("Henry")
    janet.visit(warehouse)
    henry.visit(warehouse)


Run this simple program. It will output something like this::

    $ python visit.py
    This is Janet.
    The warehouse contains: ['chair', 'bike', 'flashlight', 'laptop', 'couch']
    Type a thing you want to store (or empty): television   # typed in
    Janet stored the television.
    The warehouse contains: ['chair', 'bike', 'flashlight', 'laptop', 'couch', 'television']
    Type something you want to take (or empty): couch    # <-- typed in
    Janet took the couch.
    Thank you, come again!
    This is Henry.
    The warehouse contains: ['chair', 'bike', 'flashlight', 'laptop', 'television']
    Type a thing you want to store (or empty): bricks   # <-- typed in
    Henry stored the bricks.
    The warehouse contains: ['chair', 'bike', 'flashlight', 'laptop', 'television', 'bricks']
    Type something you want to take (or empty): bike   # <-- typed in
    Henry took the bike.
    Thank you, come again!


phase 2: first Pyro version
^^^^^^^^^^^^^^^^^^^^^^^^^^^
That wasn't very exciting but you now have working code for the basics of the warehouse system.
Now you'll use Pyro to turn the warehouse into a standalone component, that people from other
computers can visit. You'll need to add a couple of lines to the :file:`warehouse.py` file so that it will
start a Pyro server for the warehouse object. The easiest way to do this is to create the object
that you want to make available as Pyro object, and register it with a 'Pyro daemon' (the server that
listens for and processes incoming remote method calls)::

        warehouse = Warehouse()
        Pyro4.Daemon.serveSimple(
                {
                    warehouse: "example.warehouse"
                },
                ns = False)

For now, ignore the details of what exactly the :py:meth:`serveSimple` method call does.
Next up is addding a little ``main`` function so it will be started correctly, which should
make the code now look like this (:file:`warehouse.py`)::

    from __future__ import print_function
    import Pyro4
    import person


    class Warehouse(object):
        def __init__(self):
            self.contents = ["chair", "bike", "flashlight", "laptop", "couch"]

        def list_contents(self):
            return self.contents

        def take(self, name, item):
            self.contents.remove(item)
            print("{0} took the {1}.".format(name, item))

        def store(self, name, item):
            self.contents.append(item)
            print("{0} stored the {1}.".format(name, item))


    def main():
        warehouse = Warehouse()
        Pyro4.Daemon.serveSimple(
                {
                    warehouse: "example.warehouse"
                },
                ns = False)

    if __name__=="__main__":
        main()


Start the warehouse in a new console window, it will print something like this::

    $ python warehouse.py
    Object <__main__.Warehouse object at 0x025F4FF0>:
        uri = PYRO:example.warehouse@localhost:51279
    Pyro daemon running.

It will become clear what you need to do with this output in a second.
You now need to slightly change the :file:`visit.py` script that runs the thing. Instead of creating a warehouse
directly and letting the persons visit that, it is going to use Pyro to connect to the stand alone warehouse
object that you started above. It needs to know the location of the warehouse object before
it can connect to it. This is the **uri** that is printed by the warehouse program above (``PYRO:example.warehouse@localhost:51279``).
You'll need to ask the user to enter that uri string into the program, and use Pyro to
create a `proxy` to the remote object::

    uri = input("Enter the uri of the warehouse: ").strip()
    warehouse = Pyro4.Proxy(uri)

That is all you need to change. Pyro will transparently forward the calls you make on the
warehouse object to the remote object, and return the results to your code. So the code will now look like this (:file:`visit.py`)::

    # This is the code that visits the warehouse.
    import sys
    import Pyro4
    from person import Person

    if sys.version_info<(3,0):
        input = raw_input

    uri = input("Enter the uri of the warehouse: ").strip()
    warehouse = Pyro4.Proxy(uri)
    janet = Person("Janet")
    henry = Person("Henry")
    janet.visit(warehouse)
    henry.visit(warehouse)


Notice that the code of ``Warehouse`` and ``Person`` classes didn't change *at all*.

Run the program. It will output something like this::

    $ python visit.py
    Enter the uri of the warehouse: PYRO:example.warehouse@localhost:51279  # copied from warehouse output
    This is Janet.
    The warehouse contains: ['chair', 'bike', 'flashlight', 'laptop', 'couch']
    Type a thing you want to store (or empty): television   # typed in
    The warehouse contains: ['chair', 'bike', 'flashlight', 'laptop', 'couch', 'television']
    Type something you want to take (or empty): couch   # <-- typed in
    Thank you, come again!
    This is Henry.
    The warehouse contains: ['chair', 'bike', 'flashlight', 'laptop', 'television']
    Type a thing you want to store (or empty): bricks   # <-- typed in
    The warehouse contains: ['chair', 'bike', 'flashlight', 'laptop', 'television', 'bricks']
    Type something you want to take (or empty): bike    # <-- typed in
    Thank you, come again!

And notice that in the other console window, where the warehouse server is running, the following is printed::

    Janet stored the television.
    Janet took the couch.
    Henry stored the bricks.
    Henry took the bike.

phase 3: final Pyro version
^^^^^^^^^^^^^^^^^^^^^^^^^^^
The code from the previous phase works fine and could be considered to be the final program,
but is a bit cumbersome because you need to copy-paste the warehouse URI all the time to be able to use it.
You will simplify it a bit in this phase by using the Pyro name server.
Also, you will use the Pyro excepthook to print a nicer exception message
if anything goes wrong (by taking something from the warehouse that is not present! Try that now with the code
from phase 2. You will get a ``ValueError: list.remove(x): x not in list`` but with a not so useful stack trace).

.. Note::
  Once again you can leave code of the ``Warehouse`` and ``Person`` classes **unchanged**. As you can see,
  Pyro is not getting in your way at all here. You can often use it with only adding a couple of lines to your existing code.

Okay, stop the warehouse program from phase 2 if it is still running, and check if the name server
that you started in `Starting a name server`_ is still running in its own console window.

In :file:`warehouse.py` locate the statement ``Pyro4.Daemon.serveSimple(...`` and change the ``ns = False`` argument to ``ns = True``.
This tells Pyro to use a name server to register the objects in.
(The ``Pyro4.Daemon.serveSimple`` is a very easy way to start a Pyro server but it provides very little control.
Look here :ref:`server-servesimple` for some more details, and
you will learn about another way of starting a server in `Building a Stock market simulator`_).


In :file:`visit.py` remove the input statement that asks for the warehouse uri, and change the way the warehouse proxy
is created. Because you are now using a name server you can ask Pyro to locate the warehouse object automatically::

    warehouse = Pyro4.Proxy("PYRONAME:example.warehouse")

Finally, install the ``Pyro4.util.excepthook`` as excepthook. You'll soon see what this does to the exceptions and
stack traces your program produces when something goes wrong with a Pyro object.
So the code should look something like this (:file:`visit.py`)::

    # This is the code that visits the warehouse.
    import sys
    import Pyro4
    import Pyro4.util
    from person import Person

    sys.excepthook = Pyro4.util.excepthook

    warehouse = Pyro4.Proxy("PYRONAME:example.warehouse")
    janet = Person("Janet")
    henry = Person("Henry")
    janet.visit(warehouse)
    henry.visit(warehouse)


Start the warehouse program again in a separate console window. It will print something like this::

    $ python warehouse.py
    Object <__main__.Warehouse object at 0x02496050>:
        uri = PYRO:obj_426e82eea7534fb5bc78df0b5c0b6a04@localhost:51294
        name = example.warehouse
    Pyro daemon running.

As you can see the uri is different this time, it now contains some random id code instead of a name.
However it also printed an object name. This is the name that is now used in the name server for your warehouse
object. Check this with the 'nsc' tool: :command:`python -m Pyro4.nsc list` (or simply: :command:`pyro4-nsc list`), which will print something like::

    --------START LIST
    Pyro.NameServer --> PYRO:Pyro.NameServer@localhost:9090
    example.warehouse --> PYRO:obj_426e82eea7534fb5bc78df0b5c0b6a04@localhost:51294
    --------END LIST

This means you can now refer to that warehouse object using the name ``example.warehouse`` and Pyro will locate
the correct object for you automatically. This is what you changed in the :file:`visit.py` code so run that now
to see that it indeed works!

**Remote exception:** You also installed Pyro's custom excepthook so try that out. Run the :file:`visit.py` script
and try to take something from the warehouse that is not present (for instance, batteries)::

    Type something you want to take (or empty): batteries
    Traceback (most recent call last):
      File "visit.py", line 12, in <module>
        janet.visit(warehouse)
      File "d:\PROJECTS\Pyro4\examples\warehouse\phase3\person.py", line 14, in visit
        self.retrieve(warehouse)
      File "d:\PROJECTS\Pyro4\examples\warehouse\phase3\person.py", line 25, in retrieve
        warehouse.take(self.name, item)
      File "d:\PROJECTS\Pyro4\src\Pyro4\core.py", line 161, in __call__
        return self.__send(self.__name, args, kwargs)
      File "d:\PROJECTS\Pyro4\src\Pyro4\core.py", line 314, in _pyroInvoke
        raise data
    ValueError: list.remove(x): x not in list
     +--- This exception occured remotely (Pyro) - Remote traceback:
     | Traceback (most recent call last):
     |   File "d:\PROJECTS\Pyro4\src\Pyro4\core.py", line 824, in handleRequest
     |     data=method(*vargs, **kwargs)   # this is the actual method call to the Pyro object
     |   File "warehouse.py", line 14, in take
     |     self.contents.remove(item)
     | ValueError: list.remove(x): x not in list
     +--- End of remote traceback


What you can see now is that you not only get the usual exception traceback, *but also the exception
that occurred in the remote warehouse object on the server* (the "remote traceback"). This can greatly
help locating problems! As you can see it contains the source code lines from the warehouse code that
is running in the server, as opposed to the normal local traceback that only shows the remote method
call taking place inside Pyro...


.. index::
    double: tutorial; stock market example

Building a Stock market simulator
=================================

.. hint:: All of the code of this part of the tutorial can be found in the :file:`examples/stockquotes` directory.

You'll build a simple stock quote system.
The idea is that we have multiple stock markets producing stock symbol
quotes. There is an aggregator that combines the quotes from all stock
markets. Finally there are multiple viewers that can register themselves
by the aggregator and let it know what stock symbols they're interested in.
The viewers will then receive near-real-time stock quote updates for the
symbols they selected.  (Everything is fictional, of course):

============= ====== ========== ====== ========
Stockmarket 1 |rarr|            |rarr| Viewer 1
Stockmarket 2 |rarr| Aggregator |rarr| Viewer 2
     ...                                 ...
Stockmarket N |rarr|            |rarr| Viewer N
============= ====== ========== ====== ========


phase 1: simple prototype
^^^^^^^^^^^^^^^^^^^^^^^^^
Again, like the previous application (the warehouse), you first create a working
version of the system by only using normal Python code.
This simple prototype will be functional but everything will be running in a single process.
It contains no Pyro code at all, but shows what the system is going to look like later on.

First create a file :file:`stockmarket.py` that will simulate a stock market that is producing
stock quotes for registered companies. You should be able to add a 'listener' to it that will
be receiving stock quote updates. It should be able to report the stock symbols that are being
traded in this market as well. The code is as follows::

    # stockmarket.py
    import random

    class StockMarket(object):
        def __init__(self, marketname, symbols):
            self.name = marketname
            self.symbolmeans = {}
            for symbol in symbols:
                self.symbolmeans[symbol] = random.uniform(20, 200)
            self.aggregators = []

        def generate(self):
            quotes = {}
            for symbol, mean in self.symbolmeans.items():
                if random.random() < 0.2:
                    quotes[symbol] = round(random.normalvariate(mean, 20), 2)
            for aggregator in self.aggregators:
                aggregator.quotes(self.name, quotes)

        def listener(self,aggregator):
            self.aggregators.append(aggregator)

        def symbols(self):
            return self.symbolmeans.keys()


Then we need an :file:`aggregator.py` that combines all stock symbol quotes from all stockmarkets into one 'stream'
(this is the object that will be the 'listener' for the stock markets).
It should be possible to register one or more 'viewers' with the stock symbols that viewer is interested in, so
that every viewer is only receiving the stock symbols it wants. The code is like this::

    # aggregator.py
    class Aggregator(object):
        def __init__(self):
            self.viewers = {}
            self.symbols = []

        def add_symbols(self, symbols):
            self.symbols.extend(symbols)

        def available_symbols(self):
            return self.symbols

        def view(self, viewer, symbols):
            self.viewers[viewer] = symbols

        def quotes(self, market, stockquotes):
            for symbol, value in stockquotes.items():
                for viewer, symbols in self.viewers.items():
                    if symbol in symbols:
                        viewer.quote(market, symbol, value)


The :file:`viewer.py` itself is an extremely simple object that just prints out the stock symbol quotes it receives::

    # viewer.py
    from __future__ import print_function

    class Viewer(object):
        def quote(self, market, symbol, value):
            print("{0}.{1}: {2}".format(market, symbol, value))


Finally you need to write a :file:`main.py` that imports the above modules, creates all objects, creates a few
companies that are traded on the market, connects them together, and contains a loop that drives the stock market quote generation.
Because we are not yet using Pyro here, it just creates two ``Stockmarket`` objects (with a name and the companies being traded).
A single ``Aggregator`` object is registered with both markets, to receive all updates.
A ``Viewer`` object is created and connected to the ``Aggregator`` with a few companies that the viewer wants to receive quotes from.
The code is like this::

    # main.py
    from __future__ import print_function
    import time
    from stockmarket import StockMarket
    from aggregator import Aggregator
    from viewer import Viewer

    def main():
        nasdaq = StockMarket("NASDAQ", ["AAPL", "CSCO", "MSFT", "GOOG"])
        newyork = StockMarket("NYSE", ["IBM", "HPQ", "BP"])

        agg = Aggregator()
        agg.add_symbols(nasdaq.symbols())
        agg.add_symbols(newyork.symbols())
        print("aggregated symbols:", agg.available_symbols())

        nasdaq.listener(agg)
        newyork.listener(agg)

        view = Viewer()
        agg.view(view, ["IBM", "AAPL", "MSFT"])
        print("")
        while True:
            nasdaq.generate()
            newyork.generate()
            time.sleep(0.5)

    if __name__ == "__main__":
        main()


If you now run :file:`main.py` it will print a stream of stock symbol quote updates that are being generated by the two
stock markets (but only the few symbols that the viewer wants to see)::

    $ python main.py
    aggregated symbols: ['GOOG', 'AAPL', 'CSCO', 'MSFT', 'HPQ', 'BP', 'IBM']

    NYSE.IBM: 74.31
    NYSE.IBM: 108.68
    NASDAQ.AAPL: 64.17
    NYSE.IBM: 83.19
    NYSE.IBM: 92.5
    NASDAQ.AAPL: 63.09
    NASDAQ.MSFT: 161.3
    ....

phase 2: separation
^^^^^^^^^^^^^^^^^^^

.. note:: For brevity, the code for this phase of the stockquote tutorial is not shown. If you want to see it,
   have a look at the :file:`stockquotes` example, :file:`phase2`.

This phase still contains no Pyro code, but you can already make the three components more autonomous than they were in phase 1.
This step is optional, you can skip it and continue with `phase 3: Pyro version`_ below if you want.

In this phase, every component of our stock market system now has a main function that starts up the component and connects
it to the other component(s). As the stock market is the source of the data, you create a daemon thread in :file:`stockmarket.py` for it
so that all markets produces stock quote changes in the background.
:file:`main.py` is a lot simpler now: it only starts the various components and then sits to wait for an exit signal.

The idea in this phase is that you tweak the existing code a little to make it suitable to be split up in different,
autonomous components:

- it helps to add a few debug print or log statements so that you can see what is going on in each component
- each component will need some form of a 'main' or 'startup' function to create and launch it
- the main program just needs to make sure the components are started.

phase 3: Pyro version
^^^^^^^^^^^^^^^^^^^^^
Finally you use Pyro to make the various components fully distributed. Pyro is used to make them talk to each other.
The actual code for each component class hasn't changed since phase 1, it is just the plumbing that you need to write to
glue them together. Pyro is making this a matter of just a few lines of code that is Pyro-specific, the rest of the
code is needed anyway to start up and configure the system. To be able to see the final result, the code is listed
once more with comments on what changed with respect to the version in phase 1 (phase 2 is optional, it just makes
for an easier transition).

.. note::
    This time we won't be using :py:meth:`serveSimple` to publish the objects and start the Daemon.
    Instead, a daemon is created manually, we register our own objects,
    and start the request loop ourselves. This needs more code but gives you more control.


main
----
There's no :file:`main.py` anymore. This is because you now start every component by itself, in separate
console windows for instance. They run autonomously without the need of a 'main' program to start it all up in one place.

stockmarket
-----------
The :file:`stockmarket.py` gained a few print statements to see what is going on while it is running.
*Important:* there is *a single* change in the code to make it work with Pyro. Because Pyro needs to transfer
objects over the network, it requires those objects to be serializable. The ``symbols`` method returned the ``keys()``
of the dictionary of symbols in the stockmarket. While this is a normal list in Python 2, it is a ``dict_keys`` object
in Python 3. These cannot be serialized (because it is a special iterator object). The simple solution is to
force the method to build a list and return that: ``list(dictionary.keys())``.

It also gained a ``run`` method that will be running inside the background thread to generate stock quote updates.
The reason this needs to run in a thread is because the ``Stockmarket`` itself is also a Pyro object that must
listen to remote method calls (in this case, of the ``Aggregator`` object(s) that want to listen to it).
You can also choose to run the Pyro daemon loop in a background thread and generate stock quotes update in the main
thread, that doesn't matter, as long as they run independently.

Finally it gained a ``main`` function to create a couple of stock markets as we did before.
This time however they're registered as Pyro objects with the Pyro daemon. They're also entered in the
name server as ``example.stockmarket.<name>`` so the ``Aggregator`` can find them easily.

The complete code for :file:`stockmarket.py` is now as follows::

    # stockmarket.py
    from __future__ import print_function
    import random
    import threading
    import time
    import Pyro4


    class StockMarket(object):
        def __init__(self, marketname, symbols):
            self.name = marketname
            self.symbolmeans = {}
            for symbol in symbols:
                self.symbolmeans[symbol] = random.uniform(20, 200)
            self.aggregators = []

        def generate(self):
            quotes = {}
            for symbol, mean in self.symbolmeans.items():
                if random.random() < 0.2:
                    quotes[symbol] = round(random.normalvariate(mean, 20), 2)
            print("new quotes generated for", self.name)
            for aggregator in self.aggregators:
                aggregator.quotes(self.name, quotes)

        def listener(self,aggregator):
            print("market {0} adding new aggregator".format(self.name))
            self.aggregators.append(aggregator)

        def symbols(self):
            return list(self.symbolmeans.keys())

        def run(self):
            def generate_symbols():
                while True:
                    time.sleep(random.random())
                    self.generate()
            thread = threading.Thread(target=generate_symbols)
            thread.setDaemon(True)
            thread.start()


    def main():
        nasdaq = StockMarket("NASDAQ", ["AAPL", "CSCO", "MSFT", "GOOG"])
        newyork = StockMarket("NYSE", ["IBM", "HPQ", "BP"])

        daemon = Pyro4.Daemon()
        nasdaq_uri = daemon.register(nasdaq)
        newyork_uri = daemon.register(newyork)
        ns = Pyro4.locateNS()
        ns.register("example.stockmarket.nasdaq", nasdaq_uri)
        ns.register("example.stockmarket.newyork", newyork_uri)

        nasdaq.run()
        newyork.run()
        print("Stockmarkets running.")
        daemon.requestLoop()

    if __name__ == "__main__":
        main()


aggregator
----------

The :file:`aggregator.py` also gained a print function to be able to see in its console window what is going on
when a new viewer connects. The ``main`` function creates it, and connects it as a Pyro object to the Pyro daemon.
It also registers it with the name server as ``example.stockquote.aggregator`` so it can be easily retrieved by
any viewer that is interested.

*How it connects to the available stock markets:* Remember that the stock market objects registered with the name server
using a name of the form ``example.stockmarket.<name>``. It is possible to query the Pyro name server in such a way
that it returns a list of all objects matching a name pattern. This is exactly what the aggregator does, it asks
for all names starting with ``example.stockmarket.`` and for each of those, creates a Pyro proxy to that stock market.
It then registers itself as a listener with that remote stock market object.
Finally it starts the daemon loop to wait for incoming calls from any interested viewers.

The complete code for :file:`aggregator.py` is now as follows::

    # aggregator.py
    from __future__ import print_function
    import Pyro4


    class Aggregator(object):
        def __init__(self):
            self.viewers = {}
            self.symbols = []

        def add_symbols(self, symbols):
            self.symbols.extend(symbols)

        def available_symbols(self):
            return self.symbols

        def view(self, viewer, symbols):
            print("aggregator gets a new viewer, for symbols:", symbols)
            self.viewers[viewer] = symbols

        def quotes(self, market, stockquotes):
            for symbol, value in stockquotes.items():
                for viewer, symbols in self.viewers.items():
                    if symbol in symbols:
                        viewer.quote(market, symbol, value)


    def main():
        aggregator = Aggregator()
        daemon = Pyro4.Daemon()
        agg_uri = daemon.register(aggregator)
        ns = Pyro4.locateNS()
        ns.register("example.stockquote.aggregator", agg_uri)
        for market, market_uri in ns.list(prefix="example.stockmarket.").items():
            print("joining market", market)
            stockmarket = Pyro4.Proxy(market_uri)
            stockmarket.listener(aggregator)
            aggregator.add_symbols(stockmarket.symbols())
        if not aggregator.available_symbols():
            raise ValueError("no symbols found! (have you started the stock market first?)")
        print("Aggregator running. Symbols:", aggregator.available_symbols())
        daemon.requestLoop()

    if __name__ == "__main__":
        main()


viewer
------
You don't need to change the ``Viewer`` at all, besides the ``main`` function that needs to be added to start it up by itself.
It needs to create a viewer object and register it with a Pyro daemon to be able to receive stock quote update calls.
You can connect it to a running aggregator simply by asking Pyro to look that up in the name server. That can be done
by using the special ``PYRONAME:<object name>`` uri format. For the aggregator that would be: ``PYRONAME:example.stockquote.aggregator``
(because ``example.stockquote.aggregator`` is the name the aggregator used to register itself with the name server).

It is also nice to ask the user for a list of stock symbols he is interested in so do that and register the
viewer with the aggregator, passing the list of entered stock symbols to filter on.

Finally start the daemon loop to wait for incoming calls. The code is as follows::

    # viewer.py
    from __future__ import print_function
    import sys
    import Pyro4

    if sys.version_info < (3,0):
        input = raw_input


    class Viewer(object):
        def quote(self, market, symbol, value):
            print("{0}.{1}: {2}".format(market, symbol, value))


    def main():
        viewer = Viewer()
        daemon = Pyro4.Daemon()
        daemon.register(viewer)
        aggregator = Pyro4.Proxy("PYRONAME:example.stockquote.aggregator")
        print("Available stock symbols:", aggregator.available_symbols())
        symbols = input("Enter symbols you want to view (comma separated):")
        symbols = [symbol.strip() for symbol in symbols.split(",")]
        aggregator.view(viewer, symbols)
        print("Viewer listening on symbols", symbols)
        daemon.requestLoop()

    if __name__ == "__main__":
        main()


running the final program
-------------------------
To run the final stock quote system you need to do the following:

- Open a new console window and start the Pyro name server (:command:`python -m Pyro4.naming`, or simply: :command:`pyro4-ns`).

After that, start the following, each in a separate console window (so they run in parallel, and don't mix up eachother's output):

- start the stock market
- start the aggregator
- start one or more of the viewers.

The output of the stock market looks like this::

    $ python stockmarket.py
    Stockmarkets running.
    new quotes generated for NASDAQ
    new quotes generated for NASDAQ
    new quotes generated for NYSE
    new quotes generated for NASDAQ
    ...

The output of the aggregator looks like this::

    $ python aggregator.py
    joining market example.stockmarket.newyork
    joining market example.stockmarket.nasdaq
    Aggregator running. Symbols: ['HPQ', 'BP', 'IBM', 'GOOG', 'AAPL', 'CSCO', 'MSFT']
    aggregator gets a new viewer, for symbols: ['GOOG', 'CSCO', 'BP']

The output of the viewer looks like this::

    $ python viewer.py
    Available stock symbols: ['HPQ', 'BP', 'IBM', 'GOOG', 'AAPL', 'CSCO', 'MSFT']
    Enter symbols you want to view (comma separated):GOOG,CSCO,BP    # <---- typed in
    Viewer listening on symbols ['GOOG', 'CSCO', 'BP']
    NYSE.BP: 88.96
    NASDAQ.GOOG: -9.61
    NYSE.BP: 113.8
    NASDAQ.CSCO: 125.11
    NYSE.BP: 77.43
    NASDAQ.GOOG: 17.64
    NASDAQ.CSCO: 157.21
    NASDAQ.GOOG: 7.59
    ...

If you're interested to see what the name server now contains, type :command:`python -m Pyro4.nsc list` (or simply: :command:`pyro4-nsc list`)::

    $ pyro4-nsc list
    --------START LIST
    Pyro.NameServer --> PYRO:Pyro.NameServer@localhost:9090
    example.stockmarket.nasdaq --> PYRO:obj_fc742f1656bd4c7e80bee17c33787147@localhost:50510
    example.stockmarket.newyork --> PYRO:obj_6bd09853979f4d13a73263e51a9c266b@localhost:50510
    example.stockquote.aggregator --> PYRO:obj_2c7a4f5341b1464c8cc6091f3997230f@localhost:50512
    --------END LIST


.. index::
    double: tutorial; running on different machines

.. _not-localhost:

Running it on different machines
================================
For security reasons, Pyro runs stuff on localhost by default.
If you want to access things from different machines, you'll have to tell Pyro to do that explicitly.
This paragraph shows you how very briefly you can do this.
For more details, refer to the chapters in this manual about the relevant Pyro components.

*Name server*
    to start the nameserver in such a way that it is accessible from other machines,
    start it with an appropriate -n argument, like this: :command:`python -m Pyro4.naming -n your_hostname`
    (or simply: :command:`pyro4-ns -n your_hostname`)

*Warehouse server*
    You'll have to modify :file:`warehouse.py`. Right before the ``serveSimple`` call you have to tell it to bind the daemon on your hostname
    instead of localhost. One way to do this is by setting the ``HOST`` config item::

        Pyro4.config.HOST = "your_hostname_here"
        Pyro4.Daemon.serveSimple(...)

    Optional: you can choose to leave the code alone, and instead set the ``PYRO_HOST`` environment variable
    before starting the warehouse server.
    Another choice is to pass the required host (and perhaps even port) arguments to ``serveSimple``::

        Pyro4.Daemon.serveSimple(
                {
                    warehouse: "example.warehouse"
                },
                host = 'your_hostname_here',
                ns = True)

*Stock market servers*
    This example already creates a daemon object instead of using the :py:meth:`serveSimple` call.
    You'll have to modify the three source files because they all create a daemon.
    But you'll only have to add the proper ``host`` argument to the construction of the Daemon,
    to set it to your machine name instead of the default of localhost.
    Ofcourse you could also change the ``HOST`` config item (either in the code itself,
    or by setting the ``PYRO_HOST`` environment variable before launching.

Other means of creating connections
===================================
In both tutorials above we used the Name Server for easy object lookup.
The use of the name server is optional, see :ref:`name-server` for details.
There are various other options for connecting your client code to your Pyro objects,
have a look at the client code details: :ref:`object-discovery`
and the server code details: :ref:`publish-objects`.

Ok, what's next?
================

*Congratulations!*  You completed the Pyro tutorials in which you built a simple warehouse storage system,
and a stock market simulation system consisting of various independent components that talk to each other using Pyro.
The Pyro distribution archive contains a truckload of example programs with short descriptions that you could
study to see how to use the various features that Pyro has to offer. Or just browse the manual for more detailed
information. Please consider joining the Pyro mailing list (see :doc:`front page <index>`). Happy remote object programming!
