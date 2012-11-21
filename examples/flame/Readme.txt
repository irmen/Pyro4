Pyro Flame example.
Flame = "foreign location automatic module exposer"

Without actually writing any code on the server you can still write
clients that access modules and other things on the server.

You'll have to start a Pyro Flame server before running the client.
A simple way of doing this is with the following command:

  python -m Pyro4.utils.flameserver


