# The server that doesn't use the Name Server.

from __future__ import print_function
import os

import Pyro4


class QuoteGen(object):
    def quote(self):
        try:
            quote = os.popen('fortune').read()
            if len(quote) > 0:
                return quote
            return "This system cannot provide you a good fortune, install 'fortune'"
        except:
            return "This system knows no witty quotes :-("


daemon = Pyro4.core.Daemon()
quote1 = QuoteGen()
quote2 = QuoteGen()

uri1 = daemon.register(quote1)  # let Pyro create a unique name for this one
uri2 = daemon.register(quote2, "example.quotegen")  # provide a logical name ourselves

print("QuoteGen is ready, not using the Name Server.")
print("You can use the following two URIs to connect to me:")
print(uri1)
print(uri2)

daemon.requestLoop()
