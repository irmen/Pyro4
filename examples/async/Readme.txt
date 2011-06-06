This is an example that shows the asynchronous method call support.

The server has a single method that has an artificial delay of three seconds
before it returns the result of the computation.

The client shows how you might use Pyro's async feature to run the remote
method call in the background and deal with the results later (when they
are available).

