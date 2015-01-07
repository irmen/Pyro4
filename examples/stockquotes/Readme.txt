This example is the code from the Pyro tutorial where we build a simple
stock quote system.

The idea is that we have multiple stock markets producing stock symbol
quotes. There is an aggregator that combines the quotes from all stock
markets. Finally there are multiple viewers that can register themselves
by the aggregator and let it know what stock symbols they're interested in.
The viewers will then receive near-real-time stock quote updates for the
symbols they selected.  (Everything is fictional, ofcourse).


 Stockmarket  ->-----\                /----> Viewer
 Stockmarket  ->------>  Aggregator ->-----> Viewer
 Stockmarket  ->-----/                \----> Viewer


The tutorial consists of 3 phases:

phase 1:
    Simple prototype code where everything is running in a single process.
    Main.py creates all object, connects them together, and contains a loop
    that drives the stockmarket quote generation.
    This code is fully operational but contains no Pyro code at all and
    shows what the system is going to look like later on.

phase 2:
    Still no Pyro code, but the components are now more autonomous.
    They each have a main function that starts up the component and connects
    it to the other component(s). As the Stockmarket is the source of the
    data, it now contains a thread that produces stock quote changes.
    Main.py now only starts the various components and then sits to wait
    for an exit signal.
    While this phase still doesn't use Pyro at all, the structure of the
    code and the components are very close to what we want to achieve
    in the end where everything is fully distributed.

phase 3:
    The components are now fully distributed and we used Pyro to make them
    talk to each other. There is no main.py anymore because you have to start
    every component by itself: (in seperate console windows for instance)
    - start a Pyro name server (python -m Pyro4.naming).
    - start the stockmarket
    - start the aggregator
    - start one or more of the viewers.


A lot of subjects are not addressed in this tutorial, such as what to do when
one or more of the viewers quits (error handling and unregistration),
what to do when a new stockmarket is opening when we have a system
running already, what if a viewer is blocking the processing of the stock
quote updates, etc.


Note that phase 3 of this example makes use of Pyro's AutoProxy feature. Sending
pyro objects 'over the wire' will automatically convert them into proxies so
that the other side will talk to the actual object, instead of a local copy.
This is how the aggregator makes itself known to the stockmarket and the viewer
makes itself known to the aggregator.