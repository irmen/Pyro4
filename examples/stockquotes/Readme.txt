This example is the code from the Pyro tutorial where a simple stock quote
system is built.  It processes a stream of stock symbol quotes.


The idea is that we have multiple stock markets producing stock symbol
quotes. The viewer application aggregates all quotes from all the markets
and filters them so you only see the ones you're interested in.


 Stockmarket  ->-----\
 Stockmarket  ->------>------> Aggregator/Filter/Viewer
 Stockmarket  ->-----/


There's a big simplification here in that the stockmarkets not really
produce quote events themselves, instead they return quotes when asked for.
But as this is an example, it is sufficient.
A more elaborate example where there can be more viewers and the stockmarkets
decide themselves when a new quote is available, can be found in the
example 'stockquotes-old'.  It uses callbacks instead of generators.


The tutorial here consists of 3 phases:

phase 1:
    Simple prototype code where everything is running in a single process.
    viewer.py is the main program that creates all objects, connects them
    together, and runs the main loop to display stock quotes.
    This code is fully operational but contains no Pyro code at all.
    It just shows what the system is going to look like later on.

phase 2:
    The components are now distributed and we use Pyro to make them
    talk to each other. You have to start both component by itself
    (in separate console windows for instance):
    - start a Pyro name server (python -m Pyro4.naming).
    - start the stockmarket.py (it will create several different markets)
    - start the viewer.py to see the stream of quotes coming in.

    The code of the classes themselves is almost identical to phase1,
    including attribute access and the use of generator functions.
    The only thing we had to change is to create properties for the
    attributes that are accessed, and adding an expose decorator.
    Support for remote iterators/generators is available since Pyro 4.49.
    In the viewer we didn't hardcode the stock market names but instead
    we ask the name server for all available stock markets.

phase 3:
    Similar to phase2, but now we make two small changes:
    a) we use the Pyro name server in such a way that it is accessible 
    from other machines, and b) we run the stock market server in a way 
    that the host is not "localhost" by default and can be accessed by 
    different machines. To do this, create the daemon with the 
    arguments 'host' and 'port' set (i.e. host=HOST_IP, port=HOST_PORT). 
    Again, you have to start both component by itself (in separate 
    console windows for instance):
    - start a Pyro name server like this:
    (python -m Pyro4.naming -n 192.168.1.99 -p 9091) or
    (pyro4-ns -n 192.168.1.99 -p 9091)
    - start the stockmarket.py (set HOST_IP and HOST_PORT accordingly. 
    Also, make sure HOST_PORT is already open).
    - start the viewer.py in different remote machines to see the stream 
    of quotes coming in on each window.
