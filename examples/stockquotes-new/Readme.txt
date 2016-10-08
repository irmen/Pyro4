This example is the code from the Pyro tutorial where a simple stock quote
system is built.  It processes a stream of stock symbol quotes.


The idea is that we have multiple stock markets producing stock symbol
quotes. There is an aggregator that combines the quotes from all stock
markets. Finally there is a viewer that can connect to the aggregator
and display the stock quotes that they're interested in.


 Stockmarket  ->-----\
 Stockmarket  ->------>  Aggregator ->-----> Viewer
 Stockmarket  ->-----/


There are 2 major simplifications in this example to keep the code short:
- there can be only one viewer.
- a stockmarket always produces a stock quote when asked.


A more elaborate example where there can be more viewers and the stockmarkets
decide themselves when a new quote is available, can be found in the
example 'stockquotes-old'.  It's more complex and uses callbacks instead of
generators.


The tutorial here consists of 2 phases:

phase 1:
    Simple prototype code where everything is running in a single process.
    viewer.py creates all object, connects them together, and runs the main
    loop to display stock quotes.
    This code is fully operational but contains no Pyro code at all.
    It just shows what the system is going to look like later on.

phase 2:
    The components are now distributed and we use Pyro to make them
    talk to each other. You have to start every component by itself
    (in seperate console windows for instance):
    - start a Pyro name server (python -m Pyro4.naming).
    - start the stockmarket.py (it will create several different markets)
    - start the aggregator.py
    - finally start the viewer.py to see the stream of quotes coming in.

    The code of the classes themselves is almost identical to phase1,
    including attribute access and the use of generator functions.
    The only thing we had to change is to create properties for the
    attributes that are accessed, and adding an expose decorator.
    Support for remote iterators/generators is available since Pyro 4.49.
