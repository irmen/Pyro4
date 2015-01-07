from __future__ import print_function
import Pyro4


class Aggregator(object):
    def __init__(self):
        self.viewers = {}
        self.symbols = []

    def add_symbols(self, symbols):
        self.symbols.extend(symbols)

    def available_symbols(self):
        return self.symbols

    def view(self, viewer, symbols):
        print("aggregator gets a new viewer, for symbols:", symbols)
        self.viewers[viewer] = symbols

    def quotes(self, market, stockquotes):
        for symbol, value in stockquotes.items():
            for viewer, symbols in self.viewers.items():
                if symbol in symbols:
                    viewer.quote(market, symbol, value)


def main():
    aggregator = Aggregator()
    daemon = Pyro4.Daemon()
    agg_uri = daemon.register(aggregator)
    ns = Pyro4.locateNS()
    ns.register("example.stockquote.aggregator", agg_uri)
    for market, market_uri in ns.list(prefix="example.stockmarket.").items():
        print("joining market", market)
        stockmarket = Pyro4.Proxy(market_uri)
        stockmarket.listener(aggregator)
        aggregator.add_symbols(stockmarket.symbols())
    if not aggregator.available_symbols():
        raise ValueError("no symbols found! (have you started the stock market first?)")
    print("Aggregator running. Symbols:", aggregator.available_symbols())
    daemon.requestLoop()


if __name__ == "__main__":
    main()
