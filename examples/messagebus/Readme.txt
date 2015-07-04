Shows how to build a simple asynchronous pubsub message bus.
It uses a few Pyro constructs to achieve this:

- autoproxy  (for subscribers)
- the expose decorator
- instance_mode
- auto reconnect


You can run multiple publishers at the same time, make sure you give
a different location argument when you start each of them to see the results.
You can also run multiple subscribers at the same time, the published
messages will be delivered to each subscriber.


The messagebus is very simplistic if you use the in-memory storage:
It only keeps messages and subscribers in memory. If the message bus server
dies, everything is lost. If an error occurs when forwarding a message to subscribers,
the message is immediately discarded. If it was a communication error,
the subscriber is immediately removed from the topic as well.
The in-memory storage is VERY fast though, so if you're after a very high
message troughput, it may be the storage option for you.

However you can also use the SqliteStorage which uses a sqlite database
to store topics, messages and subscriptions. If the message bus server dies,
it will simply continue where it was. No messages will get lost, and it
also remembers the subscribers. So simply restarting the message bus server
is enough to get everything back on track without lost data.
The sqlite storage is quite slow tough, so if you need a very high message
troughput, it may not be suitable.


@todo maybe promote this into Pyro4.utils?
