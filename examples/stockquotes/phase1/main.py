from __future__ import print_function
import time
from stockmarket import StockMarket
from aggregator import Aggregator
from viewer import Viewer

def main():
    nasdaq=StockMarket("NASDAQ", ["AAPL", "CSCO", "MSFT", "GOOG"])
    newyork=StockMarket("NYSE", ["IBM", "HPQ", "BP"])

    agg=Aggregator()
    agg.add_symbols(nasdaq.symbols())
    agg.add_symbols(newyork.symbols())
    print("aggregated symbols:", agg.available_symbols())

    nasdaq.listener(agg)
    newyork.listener(agg)

    view=Viewer()
    agg.view(view, ["IBM", "AAPL", "MSFT"])
    print("")
    while True:
        nasdaq.generate()
        newyork.generate()
        time.sleep(0.5)

if __name__ == "__main__":
    main()
