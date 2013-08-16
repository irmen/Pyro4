A simple distributed computing example with "pull" model.
There is a single central work dispatcher/gatherer that is contacted
by every worker you create. The worker asks the dispatcher for a chunk
of work data and returns the results when it is done.

The worker in this example finds the prime factorials for the numbers
that it gets as 'work' from the dispatcher, and returns the list of
factorials as 'result' to the dispatcher.

The client program generates a list of random numbers and sends
each number as a single work item to the dispatcher. It collects
the results and prints them to the screen once everything is complete.


*** Starting up ***
- We're using a Name Server:
    * configure it to allow the pickle serializer, for instance by setting
      the environment variable: PYRO_SERIALIZERS_ACCEPTED=pickle
    * start the name server.
- start the dispatcher (dispatcher.py)
- start one or more workers (worker.py). For best results, start one of
    these on every machine/CPU in your network :-)
- finally, give the system a task to solve: start the client.py program.


Note: The dispatcher is pretty braindead. It only has a single work and
result queue. Running multiple clients will probably break the system.
Improvements are left as an exercise.

Note: because custom classes are passed over the network (such as
WorkItem and queue.Empty) the pickle serializer is used.
