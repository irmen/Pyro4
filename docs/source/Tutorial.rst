Tutorial
********

This tutorial will explain a couple of basic Pyro concepts,
a little bit about the name server, and you'll learn to write a simple Pyro application.
You'll do this by writing a warehouse system and a stock market simulator,
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
The name server is a utility that provides a phone book for Pyro applications: you use it to look up a "number" by a "name".
The name in Pyro's case is the logical name of a remote object. The number is the exact location where Pyro can contact the object.
We will see later what both actually look like, and why having a name server can be useful.

.. [#commandline] Actually there are no scripts or command files included with Pyro right now.
  The command line tools are invoked by starting their package directly using the :kbd:`-m` argument 
  of the Python interpreter.

.. _starting-name-server:

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

There's another command line tool that let you interact with the name server: "nsc" (name server control tool).
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
            self.contents=["chair","bike","flashlight","laptop","couch"]  # some initial items

        def list_contents(self):
            return self.contents

        def take(self, person, item):
            self.contents.remove(item)
            print("{0} took the {1}.".format(person.name, item))

        def store(self, person, item):
            self.contents.append(item)
            print("{0} stored the {1}.".format(person.name, item))

Then there is a ``Person`` that can visit the warehouse. The person has a name and deposit and retrieve actions
on a particular warehouse. Here is the code (:file:`person.py`)::

    from __future__ import print_function
    import sys

    if sys.version_info<(3,0):
        input=raw_input


    class Person(object):
        def __init__(self, name):
            self.name=name
        def visit(self, warehouse):
            print("This is {0}.".format(self.name))
            self.deposit(warehouse)
            self.retrieve(warehouse)
            print("Thank you, come again!")
        def deposit(self, warehouse):
            print("The warehouse contains:", warehouse.list_contents())
            item=input("Type a thing you want to store (or empty): ").strip()
            if item:
                warehouse.store(self, item)
        def retrieve(self, warehouse):
            print("The warehouse contains:", warehouse.list_contents())
            item=input("Type something you want to take (or empty): ").strip()
            if item:
                warehouse.take(self, item)


Finally you need a small script that actually runs the code. It creates the warehouse and two visitors, and
makes the visitors perform their actions in the warehouse. Here is the code (:file:`visit.py`)::

    # This is the code that runs this example.
    from warehouse import Warehouse
    from person import Person

    warehouse=Warehouse()
    janet=Person("Janet")
    henry=Person("Henry")
    janet.visit(warehouse)
    henry.visit(warehouse)

Run this simple program. It will output something like this::

    $ python visit.py
    This is Janet.
    The warehouse contains: ['chair', 'bike', 'flashlight', 'laptop', 'couch']
    Type a thing you want to store (or empty): television   # typed in
    Janet stored the television.
    The warehouse contains: ['chair', 'bike', 'flashlight', 'laptop', 'couch', 'television']
    Type something you want to take (or empty): couch    # typed in
    Janet took the couch.
    Thank you, come again!
    This is Henry.
    The warehouse contains: ['chair', 'bike', 'flashlight', 'laptop', 'television']
    Type a thing you want to store (or empty): bricks   # typed in
    Henry stored the bricks.
    The warehouse contains: ['chair', 'bike', 'flashlight', 'laptop', 'television', 'bricks']
    Type something you want to take (or empty): bike   # typed in
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

        warehouse=Warehouse()
        Pyro4.Daemon.serveSimple(
                {
                    warehouse: "example.warehouse"
                },
                ns=False)

You'll also need to add a little ``main`` function so it will be started correctly, which should
make the code now look like this (:file:`warehouse.py`)::

    from __future__ import print_function
    import Pyro4
    import person


    class Warehouse(object):
        def __init__(self):
            self.contents=["chair","bike","flashlight","laptop","couch"]

        def list_contents(self):
            return self.contents

        def take(self, person, item):
            self.contents.remove(item)
            print("{0} took the {1}.".format(person.name, item))

        def store(self, person, item):
            self.contents.append(item)
            print("{0} stored the {1}.".format(person.name, item))


    def main():
        warehouse=Warehouse()
        Pyro4.Daemon.serveSimple(
                {
                    warehouse: "example.warehouse"
                },
                ns=False)

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

    uri=input("Enter the uri of the warehouse: ").strip()
    warehouse=Pyro4.Proxy(uri)

That is all you need to change. Pyro will transparently forward the calls you make on the
warehouse object to the remote object, and return the results to your code. So the code will now look like this (:file:`visit.py`)::

    # This is the code that visits the warehouse.
    import sys
    import Pyro4
    from person import Person

    if sys.version_info<(3,0):
        input=raw_input

    uri=input("Enter the uri of the warehouse: ").strip()
    warehouse=Pyro4.Proxy(uri)
    janet=Person("Janet")
    henry=Person("Henry")
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
    Type something you want to take (or empty): couch   # typed in
    Thank you, come again!
    This is Henry.
    The warehouse contains: ['chair', 'bike', 'flashlight', 'laptop', 'television']
    Type a thing you want to store (or empty): bricks   # typed in
    The warehouse contains: ['chair', 'bike', 'flashlight', 'laptop', 'television', 'bricks']
    Type something you want to take (or empty): bike    # typed in
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
that you started in :ref:`starting-name-server` is still running in its own console window.

In :file:`warehouse.py` locate the statement ``Pyro4.Daemon.serveSimple(...`` and change the ``ns=False`` argument to ``ns=True``.
This tells Pyro to use a name server to register the objects in.
(The ``Pyro4.Daemon.serveSimple`` is a very easy way to start a Pyro server but it provides very little control.
You will learn about another way of starting a server in :ref:`stockmarket-simulator`).

In :file:`visit.py` remove the input statement that asks for the warehouse uri, and change the way the warehouse proxy
is created. Because you are now using a name server you can ask Pyro to locate the warehouse object automatically::

    warehouse=Pyro4.Proxy("PYRONAME:example.warehouse")

Finally, install the ``Pyro4.util.excepthook`` as excepthook. You'll soon see what this does to the exceptions and
stack traces your program produces when something goes wrong with a Pyro object.
So the code should look something like this (:file:`visit.py`)::

    # This is the code that visits the warehouse.
    import sys
    import Pyro4
    import Pyro4.util
    from person import Person

    sys.excepthook=Pyro4.util.excepthook

    warehouse=Pyro4.Proxy("PYRONAME:example.warehouse")
    janet=Person("Janet")
    henry=Person("Henry")
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
object. Check this with the 'nsc' tool: :command:`python -m Pyro4.nsc list`, which will print something like::

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
      File "E:\projects\Pyro4\examples\warehouse\phase3\person.py", line 14, in visit
        self.retrieve(warehouse)
      File "E:\projects\Pyro4\examples\warehouse\phase3\person.py", line 25, in retrieve
        warehouse.take(self, item)
      File "E:\Projects\Pyro4\src\Pyro4\core.py", line 136, in __call__
        return self.__send(self.__name, args, kwargs)
      File "E:\Projects\Pyro4\src\Pyro4\core.py", line 248, in _pyroInvoke
        raise data
    ValueError: list.remove(x): x not in list
     +--- This exception occured remotely (Pyro) - Remote traceback:
     | Traceback (most recent call last):
     |   File "E:\Projects\Pyro4\src\Pyro4\core.py", line 766, in handleRequest
     |     data=method(*vargs, **kwargs)   # this is the actual method call to the Pyro object
     |   File "warehouse.py", line 13, in take
     |     def take(self, person, item):
     | ValueError: list.remove(x): x not in list
     +--- End of remote traceback

What you can see now is that you not only get the usual exception traceback, *but also the exception
that occurred in the remote warehouse object on the server* (the "remote traceback"). This can greatly
help locating problems! As you can see it contains the source code lines from the warehouse code that
is running in the server, as opposed to the normal local traceback that only shows the remote method
call taking place inside Pyro...

.. _stockmarket-simulator:

Building a Stock market simulator
================================

.. hint:: The code of this part of the tutorial can be found in the :file:`examples/stockquotes` directory.

You'll build a simple stock quote system.
The idea is that we have multiple stock markets producing stock symbol
quotes. There is an aggregator that combines the quotes from all stock
markets. Finally there are multiple viewers that can register themselves
by the aggregator and let it know what stock symbols they're interested in.
The viewers will then receive near-real-time stock quote updates for the
symbols they selected.  (Everything is fictional, of course)::

    Stockmarket  ->-----\                /----> Viewer
    Stockmarket  ->------>  Aggregator ->-----> Viewer
    Stockmarket  ->-----/                \----> Viewer


phase 1: simple prototype
^^^^^^^^^^^^^^^^^^^^^^^^^
*Simple prototype code where everything is running in a single process.
Main.py creates all object, connects them together, and contains a loop
that drives the stock market quote generation.
This code is fully operational but contains no Pyro code at all and
shows what the system is going to look like later on.*


phase 2: separation
^^^^^^^^^^^^^^^^^^^
*Still no Pyro code, but the components are now more autonomous.
They each have a main function that starts up the component and connects
it to the other component(s). As the Stock market is the source of the
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
every component by itself: (in separate console windows for instance)*

- start a Pyro name server (python -m Pyro4.naming)
- start the stock market
- start the aggregator
- start one or more of the viewers.
