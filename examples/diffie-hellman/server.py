import Pyro4
import Pyro4.errors
from diffiehellman import DiffieHellman

Pyro4.config.REQUIRE_EXPOSE = True
Pyro4.config.SERVERTYPE = "multiplex"


@Pyro4.expose
class SecretStuff(object):
    def process(self, message):
        if not self._pyroDaemon._pyroHmacKey:
            raise Pyro4.errors.PyroError("no hmac key has been set, can't call this method!")
        print("Got the message:", message)
        return "message was received ok"

ns = Pyro4.locateNS()
daemon = Pyro4.Daemon()
daemon._pyroHmacKey = b"will be set to shared secret key"
uri = daemon.register(SecretStuff)
ns.register("example.dh.secretstuff", uri)


@Pyro4.expose(instance_mode="session")
class KeyExchange(object):
    def __init__(self):
        print("New KeyExchange, initializing Diffie-Hellman")
        self.dh = DiffieHellman(group=14)

    def exchange_key(self, other_public_key):
        print("received a public key, calculating shared secret...")
        self.dh.make_shared_secret_and_key(other_public_key)
        print("setting new shared secret key.")
        global daemon
        daemon._pyroHmacKey = self.dh.key
        return self.dh.public_key


key_daemon = Pyro4.Daemon()
uri = key_daemon.register(KeyExchange)
ns.register("example.dh.keyexchange", uri)

ns._pyroRelease()

key_daemon.combine_loop(daemon)
print("Starting server loop...")
key_daemon.requestLoop()
