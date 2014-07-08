from __future__ import print_function
import random
import threading
import time


class StockMarket(object):
    def __init__(self, marketname, symbols):
        self.name = marketname
        self.symbolmeans = {}
        for symbol in symbols:
            self.symbolmeans[symbol] = random.uniform(20, 200)
        self.aggregators = []

    def generate(self):
        quotes = {}
        for symbol, mean in self.symbolmeans.items():
            if random.random() < 0.2:
                quotes[symbol] = round(random.normalvariate(mean, 20), 2)
        print("new quotes generated for", self.name)
        for aggregator in self.aggregators:
            aggregator.quotes(self.name, quotes)

    def listener(self, aggregator):
        print("market {0} adding new aggregator".format(self.name))
        self.aggregators.append(aggregator)

    def symbols(self):
        return self.symbolmeans.keys()

    def run(self):
        def generate_symbols():
            while True:
                time.sleep(random.random())
                self.generate()

        thread = threading.Thread(target=generate_symbols)
        thread.setDaemon(True)
        thread.start()


def main():
    nasdaq = StockMarket("NASDAQ", ["AAPL", "CSCO", "MSFT", "GOOG"])
    newyork = StockMarket("NYSE", ["IBM", "HPQ", "BP"])
    nasdaq.run()
    newyork.run()
    return [nasdaq, newyork]
