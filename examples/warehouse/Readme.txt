This example is the code from the Pyro tutorial where we build a simple
warehouse that stores items.

The idea is that there is one big warehouse that everyone can store items
in, and retrieve other items from (if they're in the warehouse).

The tutorial consists of 3 phases:

phase 1:
    Simple prototype code where everything is running in a single process.
    visit.py creates the warehouse and two visitors.
    This code is fully operational but contains no Pyro code at all and
    shows what the system is going to look like later on.

phase 2:
    Pyro is now used to make the warehouse a standalone component.
    You can still visit it of course. visit.py does need the URI of the
    warehouse however. (It is printed as soon as the warehouse is started)
    The code of the Warehouse and the Person classes is unchanged.

phase 3:
    Phase 2 works fine but is a bit cumbersome because you need to copy-paste
    the warehouse URI to be able to visit it.
    Phase 3 simplifies things a bit by using the Pyro name server.
    Also, it uses the Pyro excepthook to print a nicer exception message
    if anything goes wrong. (Try taking something from the warehouse that is
    not present!)
    The code of the Warehouse and the Person classes is still unchanged.


Note: to avoid having to deal with serialization issues, this example only
passes primitive types (strings in this case) to the remote method calls.
