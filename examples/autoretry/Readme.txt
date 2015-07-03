This is an example that shows the auto retry feature (in the client).

server.py    -- the server you need to run for this example
client.py    -- client that uses auto retry settings


The client disables and enables auto retries to show what happens.
It shows an exception when auto retries disabled and server side closed the connection, and then use auto retries to avoid the exception raising to user code.
Suggest to run the server with timeout warning output:
PYRO_LOGLEVEL=WARNING PYRO_LOGFILE={stderr} python server.py
