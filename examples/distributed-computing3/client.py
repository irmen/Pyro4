import random
import Pyro4.errors


for _ in range(100):
    # this submits 100 factorization requests to a random available pyro server that can factorize.
    # we do this in sequence but you can imagine that a whole pool of clients is submitting work in parallel.
    with Pyro4.Proxy("PYROMETA:example3.worker.factorizer") as w:
        n = number = random.randint(3211, 12000) * random.randint(4567, 21000)
        result = w.factorize(n)
        print("%s factorized %d: %s" % (w._pyroConnection.objectId, n, result))
