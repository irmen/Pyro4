from __future__ import print_function
import Pyro4


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


if __name__ == "__main__":
    view = Viewer()
    with Pyro4.Proxy("PYRONAME:example.stockquote.aggregator") as agg:
        view.aggregator(agg, ["IBM", "AAPL", "MSFT"])
        view.print_quotes()
