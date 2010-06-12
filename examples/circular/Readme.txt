Create a chain of objects calling each other:
 
client   -->  A  -->  B

              ^       |
              |       v
              | 
              `-----  C


I.e. C calls A again.
A detects that the message went full circle and returns
the result (a 'trace' of the route) to the client.
(the detection checks if the name of the current server
is already in the current trace of the route, i.e.,
if it arrives for a second time on the same server,
it concludes that we're done).

First start the three servers (servA,B,C) and then run the client.
  
You need to have a nameserver running.
