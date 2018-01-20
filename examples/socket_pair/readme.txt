Pyro 4.70 introduced the possibility to run a Pyro Daemon and Proxy over a user-supplied,
already connected socket, such as those produced by the socket.socketpair() function.

This makes it easy to communicate efficiently with a child process or background thread, using Pyro.


The pair-fork.py program uses fork() to run a background process (Windows doesn't support this)
The pair-thread.py program uses a background thread for the Pyro daemon (works on Windows too).


Note that it is fine to use pickle as serializer here because all communication is done between
threads or processes that we created ourselves and the socket is not accessible to the outside world.
