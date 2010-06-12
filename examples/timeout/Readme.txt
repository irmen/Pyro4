This is an example that shows the connection timeout handling
(in the client).

server.py    -- the server you need to run for this example
client.py    -- client that uses timeout settings


The client disables and enables timeouts to show what happens.
It shows timeouts during long remote method calls, but also timeouts
when trying to connect to a unresponsive server.
