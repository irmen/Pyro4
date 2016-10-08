from collections import defaultdict


class Aggregator(object):
    def __init__(self):
        self.symbols = set()
        self.markets = {}

    def add_symbols(self, symbols):
        self.symbols.update(symbols)

    def add_market(self, stockmarket):
        self.markets[stockmarket.name] = stockmarket

    def quotes(self):
        # for simplicity, assume that all stock markets always have new quotes.
        market_quotes = {marketname: market.quotes() for marketname, market in self.markets.items()}
        while True:
            # get the next new quote from each stockmarket
            agg_quotes = defaultdict(list)
            for marketname, marketquotes in market_quotes.items():
                quotes = next(marketquotes)
                if quotes[0] in self.symbols:
                    # only keep the quotes that we are interested in
                    agg_quotes[marketname].append(quotes)
            yield agg_quotes
