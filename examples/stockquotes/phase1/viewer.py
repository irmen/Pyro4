from __future__ import print_function
from stockmarket import StockMarket
from aggregator import Aggregator


class Viewer(object):
    def __init__(self):
        self.agg = None
        self.filter_symbols = set()

    def aggregator(self, aggregator, symbols):
        self.agg = aggregator
        self.filter_symbols.update(symbols)

    def print_quotes(self):
        print("viewed quotes:", self.filter_symbols)
        aggregated_quotes = self.agg.quotes()
        while True:
            agg_quotes = next(aggregated_quotes)
            for marketname, quotes in agg_quotes.items():
                for symbol, value in quotes:
                    if symbol in self.filter_symbols:
                        print("{0}.{1}: {2}".format(marketname, symbol, value))


def main():
    nasdaq = StockMarket("NASDAQ", ["AAPL", "CSCO", "MSFT", "GOOG"])
    newyork = StockMarket("NYSE", ["IBM", "HPQ", "BP"])

    agg = Aggregator()
    agg.add_market(nasdaq)
    agg.add_symbols(nasdaq.symbols)
    agg.add_market(newyork)
    agg.add_symbols(newyork.symbols)
    print("aggregated symbols:", agg.symbols)

    view = Viewer()
    view.aggregator(agg, ["IBM", "AAPL", "MSFT"])
    view.print_quotes()


if __name__ == "__main__":
    main()



