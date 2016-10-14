from __future__ import print_function
import Pyro4


class Viewer(object):
    def __init__(self):
        self.markets = set()
        self.symbols = set()

    def start(self):
        print("Shown quotes:", self.symbols)
        quote_sources = {
            market.name: market.quotes() for market in self.markets
        }
        while True:
            for market, quote_source in quote_sources.items():
                quote = next(quote_source)  # get a new stock quote from the source
                symbol, value = quote
                if symbol in self.symbols:
                    print("{0}.{1}: {2}".format(market, symbol, value))


def find_stockmarkets():
    # You can hardcode the stockmarket names for nasdaq and newyork, but it
    # is more flexible if we just look for every available stockmarket.
    markets = []
    with Pyro4.locateNS() as ns:
        for market, market_uri in ns.list(prefix="example.stockmarket.").items():
            print("found market", market)
            markets.append(Pyro4.Proxy(market_uri))
    if not markets:
        raise ValueError("no markets found! (have you started the stock markets first?)")
    return markets


def main():
    viewer = Viewer()
    viewer.markets = find_stockmarkets()
    viewer.symbols = {"IBM", "AAPL", "MSFT"}
    viewer.start()


if __name__ == "__main__":
    main()
