import random
import time


class StockMarket(object):
    def __init__(self, marketname, symbols):
        self.name = marketname
        self.symbols = symbols

    def quotes(self):
        while True:
            symbol = random.choice(self.symbols)
            yield symbol, round(random.uniform(5, 150), 2)
            time.sleep(random.random()/2.0)
