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
