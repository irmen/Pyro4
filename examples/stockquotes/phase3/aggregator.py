from __future__ import print_function
import Pyro4

class Aggregator(object):
    def __init__(self):
        self.viewers={}
        self.symbols=[]

    def add_symbols(self, symbols):
        self.symbols.extend(symbols)

    def available_symbols(self):
        return self.symbols

    def view(self, viewer, symbols):
        print("aggregator gets a new viewer, for symbols:", symbols)
        self.viewers[viewer]=symbols

    def quotes(self, market, stockquotes):
        for symbol, value in stockquotes.items():
            for viewer, symbols in self.viewers.items():
                if symbol in symbols:
                    viewer.quote(market, symbol, value)


def main():
    agg=Aggregator()
    daemon=Pyro4.Daemon()
    agg_uri=daemon.register(agg)
    ns=Pyro4.locateNS()
    ns.remove("stockquote.aggregator")
    ns.register("stockquote.aggregator", agg_uri)
    for market, market_uri in ns.list(prefix="stockmarket.").items():
        print("joining market", market)
        stockmarket=Pyro4.Proxy(market_uri)
        stockmarket.listener(Pyro4.Proxy(agg_uri))
        agg.add_symbols(stockmarket.symbols())
    print("Aggregator running. Symbols:", agg.available_symbols())
    daemon.requestLoop()

if __name__ == "__main__":
    main()
