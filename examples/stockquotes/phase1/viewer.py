from __future__ import print_function
from stockmarket import StockMarket


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


def main():
    nasdaq = StockMarket("NASDAQ", ["AAPL", "CSCO", "MSFT", "GOOG"])
    newyork = StockMarket("NYSE", ["IBM", "HPQ", "BP"])
    viewer = Viewer()
    viewer.markets = {nasdaq, newyork}
    viewer.symbols = {"IBM", "AAPL", "MSFT"}
    viewer.start()


if __name__ == "__main__":
    main()
