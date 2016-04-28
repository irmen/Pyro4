import Pyro4
import Pyro4.errors
from diffiehellman import DiffieHellman


dh = DiffieHellman(group=14)

with Pyro4.locateNS() as ns:
    uri = ns.lookup("example.dh.secretstuff")
    print(uri)

p = Pyro4.Proxy(uri)
try:
    p.process("hey")
    raise RuntimeError("this should not be reached")
except Pyro4.errors.PyroError as x:
    print("Error occured (expected!):", x)

with Pyro4.Proxy("PYRONAME:example.dh.keyexchange") as keyex:
    print("exchange public keys...")
    other_key = keyex.exchange_key(dh.public_key)
    print("got server public key, creating shared secret key...")
    dh.make_shared_secret_and_key(other_key)
    print("setting key on proxy.")
    p._pyroHmacKey = dh.key

print("Calling proxy again...")
result = p.process("hey")
print("Got reply:", result)
