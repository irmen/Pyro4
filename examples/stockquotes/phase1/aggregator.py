class Aggregator(object):
    def __init__(self):
        self.viewers = {}
        self.symbols = []

    def add_symbols(self, symbols):
        self.symbols.extend(symbols)

    def available_symbols(self):
        return self.symbols

    def view(self, viewer, symbols):
        self.viewers[viewer] = symbols

    def quotes(self, market, stockquotes):
        for symbol, value in stockquotes.items():
            for viewer, symbols in self.viewers.items():
                if symbol in symbols:
                    viewer.quote(market, symbol, value)
