from __future__ import print_function


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


def main(stockmarkets):
    aggregator = Aggregator()
    for market in stockmarkets:
        aggregator.add_symbols(market.symbols())
        market.listener(aggregator)
    if not aggregator.available_symbols():
        raise ValueError("no symbols found!")
    print("aggregated symbols:", aggregator.available_symbols())
    return aggregator
