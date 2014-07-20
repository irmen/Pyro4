Shows how the MAX_MESSAGE_SIZE config item works.

The client sends a big message first without a limit,
then with a limit set on the message size. The second
attempt will fail with a protocol error.

The client talks to the echo server so you'll have to start
the echo server first in another window:

$ python -m Pyro4.test.echoserver

    or:

$ pyro4-test-echoserver


You can try to set the PYRO_MAX_MESSAGE_SIZE environment variable
to a small value (such as 2000) before starting the echo server,
to see how it deals with receiving messages that are too large on the server.
(Pyro will log an error and close the connection).

