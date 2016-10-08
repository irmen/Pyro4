from __future__ import print_function
from collections import defaultdict
import Pyro4


@Pyro4.expose
class Aggregator(object):
    def __init__(self):
        self._symbols = set()
        self.markets = {}

    @property
    def symbols(self):
        return self._symbols

    def add_symbols(self, symbols):
        self._symbols.update(symbols)

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
                if quotes[0] in self._symbols:
                    # only keep the quotes that we are interested in
                    agg_quotes[marketname].append(quotes)
            yield agg_quotes


if __name__ == "__main__":
    aggregator = Aggregator()
    with Pyro4.Daemon() as daemon:
        agg_uri = daemon.register(aggregator)
        with Pyro4.locateNS() as ns:
            ns.register("example.stockquote.aggregator", agg_uri)
            for market, market_uri in ns.list(prefix="example.stockmarket.").items():
                print("joining market", market)
                stockmarket = Pyro4.Proxy(market_uri)
                aggregator.add_market(stockmarket)
                aggregator.add_symbols(stockmarket.symbols)
        if not aggregator.symbols:
            raise ValueError("no symbols found! (have you started the stock markets first?)")
        print("Aggregator running. Symbols:", aggregator.symbols)
        daemon.requestLoop()
