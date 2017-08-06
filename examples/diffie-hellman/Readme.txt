Diffie-Hellman key exchange.

Pyro supports a HMAC message digest key mechanism. You'll have to set the same key
in both your server (on the daemon) and your client (on the proxy).
It can be problematic to distribute such a shared private key among your client and server code,
as you may not want to hardcode it (especially in the client!)

There's are secure algorithms to tackle the "key exchange" problem, and this example shows
one of them: the Diffie-Hellman key exchange. It's based on calculating stuff with large prime
exponenents and modulos, but in the end, both the client and server agree on a shared secret key
that: a) has never publicly been sent over the wire, b) is not hardcoded anywhere.

This shared secret key is then used as Pyro HMAC key to authenticate the messages.


A few IMPORTANT notes:

- in this particular example there is NO ENCRYPTION done whatsoever. Encryption is a different topic!
  If you want, you can enable SSL/TLS in Pyro as well to provide this. However, if you use 2-way-ssl,
  this makes the use of the HMAC key somewhat obsolete, because mutual verification of the SSL certificates
  essentially then does the same thing. See the SSL example for more details.
- this example shows an approach on a safe way to agree on a shared secret key. It then uses this
  for Pyro's HMAC key but that's just for the sake of example.
- it's a rather silly example because in Pyro, the HMAC key is a per-daemon setting. ALL calls to objects
  on that daemon will use the same HMAC key.
  Re-connecting a new client to this example server will start a new key-exchange and reset the
  HMAC key to something else. So, only a single client can talk to this server at any time.
  That's not something you want in a real life situation!
