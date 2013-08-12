from __future__ import print_function
import sys, time
import warnings
import Pyro4

warnings.filterwarnings("ignore")

#Pyro4.config.COMMTIMEOUT=2

print("Enter the echo uri of the server:")
if sys.version_info<(3,0):
    uri=raw_input()
else:
    uri=input()
uri=uri.strip()

basesize = 500000

def do_test(data):
    totalsize = 0

    obj=Pyro4.core.Proxy(uri)
    obj._pyroBind()

    begin = time.time()
    for i in range(1,15):
        print("transferring %d bytes" % (basesize*i))
        size = obj.transfer(data*i)
        assert size==(basesize*i)
        totalsize += basesize*i
    duration = time.time()-begin

    totalsize = float(totalsize)
    print("It took %.2f seconds to transfer %d kilobyte." % (duration, totalsize/1024))
    print("That is %.0f kb/sec. = %.1f mb/sec. (serializer: %s)" % (totalsize/1024/duration, totalsize/1024/1024/duration, Pyro4.config.SERIALIZER))

data = 'x'*basesize
print("\n\n----test with string data----")
do_test(data)
print("\n\n----test with byte data----")
data = b'x'*basesize
do_test(data)
