from __future__ import print_function, division
import zipfile
import time
from collections import Counter
import Pyro4


def wordfreq(book, counter_uri):
    begin = time.time()
    with Pyro4.Proxy(counter_uri) as counter:
        totals = counter.count(book)
        totals = Counter(totals)
    time_taken = round(time.time()-begin, 2)
    print("Top five words:")
    for word, counts in totals.most_common(5):
        print("  %s (%d)" % (word, counts))
    print("Time taken:", time_taken, "sec.")


if __name__ == "__main__":
    book = zipfile.ZipFile("alice.zip").open("alice.txt", "r").read().decode("utf-8")
    book = book.splitlines()
    print("(book text consists of %d lines total)" % len(book))
    print("(artificial delays are used to dramatize the differences in execution time)")

    print("\nCounting the words using a single counter...")
    wordfreq(book, "PYRONAME:example.dc.wordcount.1")

    print("\nCounting words using multiple parallel counters...")
    wordfreq(book, "PYRONAME:example.dc.dispatcher")
