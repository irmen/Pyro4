import random


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
        for aggregator in self.aggregators:
            aggregator.quotes(self.name, quotes)

    def listener(self, aggregator):
        self.aggregators.append(aggregator)

    def symbols(self):
        return self.symbolmeans.keys()
