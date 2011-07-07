from __future__ import print_function
import sys, time
import Pyro4

#Pyro4.config.COMMTIMEOUT=2

basesize = 500000
data='x'*basesize
if sys.version_info>=(3,0):
    data=bytes(data,"ASCII")

totalsize=0

obj=Pyro4.core.Proxy("PYRONAME:example.hugetransfer")
obj._pyroBind()

begin=time.time()
for i in range(1,15):
    print("transferring %d bytes" % (basesize*i))
    size=obj.transfer(data*i)
    # print(" reply=%d" % size)
    totalsize=totalsize+basesize*i
duration=time.time()-begin

totalsize=float(totalsize)
print("It took %.2f seconds to transfer %d kilobyte." % (duration, totalsize/1024))
print("That is %.0f k/sec. = %.1f mb/sec." % (totalsize/1024/duration, totalsize/1024/1024/duration))
