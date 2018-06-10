This shows how you can pass through serialized arguments unchanged via Pyro4.core.SerializedBlob.
The idea is that you tell Pyro to NOT serialize/deserialize particular message contents,
because you'll be doing that yourself once it reaches the destination. This avoids a lot of
serializer overhead (which is quite expensive).

This way it is possible to make efficient dispatchers/proxies/routing services for Pyro,
where only the actual receiving server at the end, deserializes the package once.


Run this example by:

- make sure a Pyro name server is running.
- start a dispatcher from the dispatcher directory
- start one or more listeners from listeners/main.py
- start the client.
