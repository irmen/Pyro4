from __future__ import print_function
import sys
import time
from Pyro4.util import getPyroTraceback
import Pyro4

if sys.version_info<(3,0):
    input=raw_input

NUMBER_OF_ITERATIONS=10000

uri=input("enter server object uri: ").strip()
p=Pyro4.Proxy(uri)

# First, we do a loop of N normal remote calls on the proxy
# We time the loop and validate the computation result
print("Normal remote calls...")
begin=time.time()
total=0
for i in range(NUMBER_OF_ITERATIONS):
    total+=p.multiply(7,6)
    total+=p.add(10,20)
assert total==(NUMBER_OF_ITERATIONS*(7*6 + 10+20))   # check
duration=time.time()-begin
print("that took {0:.4f} seconds ({1:.0f} calls/sec)".format(duration, NUMBER_OF_ITERATIONS*2/duration))
duration_normal=duration


# Now we do the same loop of N remote calls but this time we use
# the batched calls proxy. It collects all calls and processes them
# in a single batch. For many subsequent calls on the same proxy this
# is much faster than doing all calls individually.
# (but it has a few limitations and requires changes to your code)
print("\nBatched remote calls...")
begin=time.time()
batch=p._pyroBatch()        # get a batched call proxy for 'p'
for i in range(NUMBER_OF_ITERATIONS):
    batch.multiply(7,6)         # queue a call, note that it returns 'None' immediately
    batch.add(10,20)            # queue a call, note that it returns 'None' immediately
print("processing the results...")
total=0
result=batch()      # execute the batch of remote calls, it returns a generator that produces all results in sequence
for r in result:
    total+=r
duration=time.time()-begin
assert total==(NUMBER_OF_ITERATIONS*(7*6 + 10+20))   # check
print("total time taken {0:.4f} seconds ({1:.0f} calls/sec)".format(duration, NUMBER_OF_ITERATIONS*2/duration))
print("batched calls were {0:.2f} times faster than normal remote calls".format(duration_normal/duration))

# Show what happens when one of the methods in a batch generates an error.
# (the batch is aborted and the error is raised locally again).
# Btw, you can re-use a batch proxy once you've called it and processed the results.
print("\nBatch with an error. Dividing a number by decreasing divisors...")
for d in range(3,-3,-1):    #  divide by 3,2,1,0,-1,-2,-3... but 0 will be a problem ;-)
    batch.divide(100,d)
print("getting results...")
divisor=3
try:
    for result in batch():
        print("100//%d = %d" % (divisor,result))
        divisor-=1
        # this will raise the proper zerodivision exception once we're about
        # to process the batch result from the divide by 0 call.
except Exception:
    print("An error occurred during the batch!")
    print("".join(getPyroTraceback()))
