This test is to find out the average time it takes for a remote
PYRO method call. Also it is a kind of stress test because lots
of calls are made in a very short time.

The oneway method call test is very fast if you run the client 
and server on different machines. If they're running on the same
machine, the speedup is less noticable.


There is also the 'connections' benchmark which tests the speed
at which Pyro can make new proxy connections. It tests the raw 
connect speed (by releasing and rebinding existing proxies) and
also the speed at which new proxies can be created that perform
a single remote method call.


Different serializers
---------------------
Note that Pyro4's performance is very much affected by two things:
1) the network latency and bandwith
2) the characteristics of your data (small messages or large)
2) the serializer that is used.

For instance, here are the numbers of the various serializers
on my system (running the benchmark on localhost):

serializer | performance (avg. time/call)
-----------+-------------------------------
   pickle  |  0.114 msec = 8781 calls/sec
  marshal  |  0.124 msec = 8068 calls/sec
     json  |  0.182 msec = 5508 calls/sec
  serpent  |  0.259 msec = 3856 calls/sec

Pickle is very fast (even faster than marshal, which I find surprising)
but it has potential security problems. Serpent, the default serializer,
is relatively slow, but is has the richest type support of the other
serializers that don't have security problems.

Don't select a serializer upfront based on the above performance chart.
It is just the simple result of this silly benchmark example. Real-world
performance may be quite different in your particular situation.

