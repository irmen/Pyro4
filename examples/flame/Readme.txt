Pyro Flame example.
Flame = "foreign location automatic module exposer"

Without actually writing any code on the server you can still write
clients that access modules and other things on the server.

You'll have to start a Pyro Flame server before running the client.
Set the correct configuration (see below) and run the following command:

  python -m Pyro4.utils.flameserver
    or:
  pyro4-flameserver

Security (explicitly enable Flame, pickle serializer
----------------------------------------------------
By default, Flame is switched off; the feature cannot be used.
This is because it has severe security implications.
If you want to use Flame, you have to explicitly enable it in
the server's configuration (FLAME_ENABLED config item).

Also, because a lot of custom classes are passed over the network,
flame requires the pickle serializer (SERIALIZER config item).
When launching the server via the above utility command, this
is taken care of automatically. If you write your own server and
client, remember to configure this correctly yourself.

For this example, setting the environment variable:
  PYRO_FLAME_ENABLED=true
before launching the flame server is enough to make it work.
