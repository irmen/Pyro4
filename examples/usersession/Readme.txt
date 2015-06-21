This example shows the use of a couple of advanced Pyro constructs to
achieve a thread safe, per-user resource connection in the Pyro server.

It utilizes:
- instance_mode "session"
- annotations to pass the 'user token' from client to server
- current_context to access the annotations in the server code
- a silly global key-value database to trigger concurrency issues

There are probably other ways of achieving the same thing (for instance,
using the client connection on the current_context instead of explicitly
passing along the user token) but it's just an example to give some inspiration.


Before starting the server make sure you have a Pyro name server running.
