from __future__ import print_function

class Viewer(object):
    def quote(self, market, symbol, value):
        print("{0}.{1}: {2}".format(market, symbol, value))


def main(aggregator):
    viewer=Viewer()
    aggregator.view(viewer, ["IBM", "AAPL", "MSFT"])
    return viewer
