A simple distributed computing example where many client jobs are
automatically distributed over a pool of workers. The load distribution
is done by not connecting to a particular pyro object, or using a dispatcher
service, but it is simply using the yellow-pages function (metadata lookup)
to find one randomly chosen object that has the required metadata tag.

It's pretty simple but is also a bit dumb; it doesn't know if the chosen
worker is idle or busy with another client's request.
Also it doesn't deal with a worker that crashed or is unreachable.
Optimizing these things is an excercise left for the reader.


*** Starting up ***
- We're using a Name Server, so start one.
- start one or more workers (the more the merrier)
- run the client
