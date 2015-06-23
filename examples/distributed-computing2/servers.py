import string
import time
from collections import Counter
from itertools import cycle
try:
    from itertools import izip_longest as zip_longest
except ImportError:
    from itertools import zip_longest
import Pyro4


@Pyro4.expose()
class WordCounter(object):
    filter_words = {'a', 'an', 'at', 'the', 'i', 'he', 'she', 's', 'but', 'was', 'has', 'had', 'have', 'and',
                    'are', 'as', 'be', 'by', 'for', 'if', 'in', 'is', 'it', 'of', 'or', 'that',
                    'the', 'to', 'with', 'his', 'all', 'any', 'this', 'that', 'not', 'from', 'on',
                    'me', 'him', 'her', 'their', 'so', 'you', 'there', 'now', 'then', 'no', 'yes',
                    'one', 'were', 'they', 'them', 'which', 'what', 'when', 'who', 'how', 'where', 'some', 'my',
                    'into', 'up', 'out', 'some', 'we', 'us', 't', 'do'}
    trans_punc = {ord(punc): u' ' for punc in string.punctuation}

    def count(self, lines):
        counts = Counter()
        for num, line in enumerate(lines):
            if line:
                line = line.translate(self.trans_punc).lower()
                interesting_words = [w for w in line.split() if w.isalpha() and w not in self.filter_words]
                counts.update(interesting_words)
            if num % 10 == 0:
                time.sleep(0.01)  # artificial delay
        return counts


def grouper(n, iterable, padvalue=None):
    """grouper(3, 'abcdefg', 'x') --> ('a','b','c'), ('d','e','f'), ('g','x','x')"""
    return zip_longest(*[iter(iterable)]*n, fillvalue=padvalue)


@Pyro4.expose()
class Dispatcher(object):
    def count(self, lines):
        # use the name server's prefix lookup to get all registered wordcounters
        all_counters = Pyro4.locateNS().list(prefix="example.dc.wordcount.")
        counters = [Pyro4.async(Pyro4.Proxy(uri)) for uri in all_counters.values()]
        roundrobin_counters = cycle(counters)

        # chop the text into chunks that can be distributed across the workers
        # uses async proxy so that we can hand off everything in parallel
        # counter is selected in a round-robin fashion from list of all available counters
        async_results = []
        for chunk in grouper(100, lines):
            counter = next(roundrobin_counters)
            result = counter.count(chunk)
            async_results.append(result)

        # gather the results
        print("Collecting %d results..." % len(async_results))
        totals = Counter()
        for result in async_results:
            totals.update(result.value)
        return totals


if __name__ == "__main__":
    print("Spinning up 5 wordcounters, and 1 dispatcher.")
    Pyro4.config.SERVERTYPE = "thread"
    Pyro4.Daemon.serveSimple(
        {
            WordCounter(): "example.dc.wordcount.1",
            WordCounter(): "example.dc.wordcount.2",
            WordCounter(): "example.dc.wordcount.3",
            WordCounter(): "example.dc.wordcount.4",
            WordCounter(): "example.dc.wordcount.5",
            Dispatcher:    "example.dc.dispatcher"
        }, verbose=False
    )
