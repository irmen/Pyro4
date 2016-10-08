from __future__ import print_function
import sys

import Pyro4


if sys.version_info < (3, 0):
    input = raw_input


@Pyro4.expose
class Viewer(object):
    def quote(self, market, symbol, value):
        print("{0}.{1}: {2}".format(market, symbol, value))


def main():
    viewer = Viewer()
    with Pyro4.Daemon() as daemon:
        daemon.register(viewer)
        aggregator = Pyro4.Proxy("PYRONAME:example.stockquote-old.aggregator")
        print("Available stock symbols:", aggregator.available_symbols())
        symbols = input("Enter symbols you want to view (comma separated):")
        symbols = [symbol.strip() for symbol in symbols.split(",")]
        aggregator.view(viewer, symbols)
        print("Viewer listening on symbols", symbols)
        daemon.requestLoop()


if __name__ == "__main__":
    main()
