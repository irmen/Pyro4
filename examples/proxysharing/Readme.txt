This example shows how Pyro deals with sharing proxies in different threads.
Due to internal locking you can freely share proxies among threads.
The lock makes sure that only a single thread is actually using the proxy's
communication channel at all times. 

This can be convenient BUT it may not be the best way. The lock essentially
prevents parallelism. If you want calls to go in parallel, give each thread
their own proxy.
