from __future__ import print_function
import sys
import time
import warnings

import Pyro4


warnings.filterwarnings("ignore")

# Pyro4.config.COMMTIMEOUT=2

print("Enter the server's uri that was printed:")
if sys.version_info < (3, 0):
    uri = raw_input()
else:
    uri = input()
uri = uri.strip()

datasize = 5 * 1024 * 1024  # 5 mb


def do_test(data):
    assert len(data) == datasize
    totalsize = 0

    obj = Pyro4.core.Proxy(uri)
    obj._pyroBind()

    begin = time.time()
    for i in range(10):
        print("transferring %d bytes" % datasize)
        size = obj.transfer(data)
        assert size == datasize
        totalsize += datasize
    duration = time.time() - begin

    totalsize = float(totalsize)
    print("It took %.2f seconds to transfer %d mb." % (duration, totalsize / 1024 / 1024))
    print("That is %.0f kb/sec. = %.1f mb/sec. (serializer: %s)" % (totalsize / 1024 / duration, totalsize / 1024 / 1024 / duration, Pyro4.config.SERIALIZER))


data = 'x' * datasize
print("\n\n----test with string data----")
do_test(data)
print("\n\n----test with byte data----")
data = b'x' * datasize
do_test(data)
data = bytearray(b'x' * datasize)
print("\n\n----test with bytearray data----")
do_test(data)
