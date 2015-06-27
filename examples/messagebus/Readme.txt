Shows how to build a simple asynchronous pubsub message bus.
It uses a few Pyro constructs to achieve this:

- autoproxy  (for subscribers)
- oneway calls
- the expose decorator
- instance_mode


The messagebus is very simplistic:
It only keeps message in memory.
If an error occurs when forwarding a message to subscribers,
the message is immediately discarded. If it was a communication
error, the subscriber is immediately removed from the topic as well.

@todo maybe promote this into Pyro4.utils?
