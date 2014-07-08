from __future__ import print_function
import sys

import stockmarket
import aggregator
import viewer


if sys.version_info < (3, 0):
    input = raw_input


def main():
    markets = stockmarket.main()
    aggr = aggregator.main(markets)
    viewer.main(aggr)
    print("\nPress enter to quit.\n")
    input()


if __name__ == "__main__":
    main()
