from __future__ import print_function
import random
import threading
import time

import Pyro4


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

    @Pyro4.expose
    def listener(self, aggregator):
        print("market {0} adding new aggregator".format(self.name))
        self.aggregators.append(aggregator)

    @Pyro4.expose
    def symbols(self):
        return list(self.symbolmeans.keys())

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

    with Pyro4.Daemon() as daemon:
        nasdaq_uri = daemon.register(nasdaq)
        newyork_uri = daemon.register(newyork)
        with Pyro4.locateNS() as ns:
            ns.register("example.stockmarket-old.nasdaq", nasdaq_uri)
            ns.register("example.stockmarket-old.newyork", newyork_uri)
        nasdaq.run()
        newyork.run()
        print("Stockmarkets running.")
        daemon.requestLoop()


if __name__ == "__main__":
    main()
