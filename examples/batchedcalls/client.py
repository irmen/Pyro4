from __future__ import print_function
import sys
import time

from Pyro4.util import getPyroTraceback
import Pyro4


if sys.version_info < (3, 0):
    input = raw_input

NUMBER_OF_LOOPS = 20000

uri = input("enter server object uri: ").strip()
p = Pyro4.Proxy(uri)

# First, we do a loop of N normal remote calls on the proxy
# We time the loop and validate the computation result
print("Normal remote calls...")
begin = time.time()
total = 0
p.printmessage("beginning normal calls")
for i in range(NUMBER_OF_LOOPS):
    total += p.multiply(7, 6)
    total += p.add(10, 20)
p.printmessage("end of normal calls")
assert total == (NUMBER_OF_LOOPS * (7 * 6 + 10 + 20))  # check
duration = time.time() - begin
print("that took {0:.2f} seconds ({1:.0f} calls/sec)".format(duration, NUMBER_OF_LOOPS * 2.0 / duration))
duration_normal = duration


# Now we do the same loop of N remote calls but this time we use
# the batched calls proxy. It collects all calls and processes them
# in a single batch. For many subsequent calls on the same proxy this
# is much faster than doing all calls individually.
# (but it has a few limitations and requires changes to your code)
print("\nBatched remote calls...")
begin = time.time()
batch = Pyro4.batch(p)  # get a batched call proxy for 'p'
batch.printmessage("beginning batch #1")
for i in range(NUMBER_OF_LOOPS):
    batch.multiply(7, 6)  # queue a call, note that it returns 'None' immediately
    batch.add(10, 20)  # queue a call, note that it returns 'None' immediately
batch.printmessage("end of batch #1")
print("processing the results...")
total = 0
result = batch()  # execute the batch of remote calls, it returns a generator that produces all results in sequence
for r in result:
    total += r
duration = time.time() - begin
assert total == (NUMBER_OF_LOOPS * (7 * 6 + 10 + 20))  # check
print("total time taken {0:.2f} seconds ({1:.0f} calls/sec)".format(duration, NUMBER_OF_LOOPS * 2.0 / duration // 100 * 100))
print("batched calls were {0:.1f} times faster than normal remote calls".format(duration_normal / duration))

# Now we do another loop of batched calls, but this time oneway (no results).
print("\nOneway batched remote calls...")
begin = time.time()
batch = Pyro4.batch(p)  # get a batched call proxy for 'p'
batch.printmessage("beginning batch #2")
for i in range(NUMBER_OF_LOOPS):
    batch.multiply(7, 6)  # queue a call, note that it returns 'None' immediately
    batch.add(10, 20)  # queue a call, note that it returns 'None' immediately
batch.delay(2)  # queue a delay of 2 seconds (but we won't notice)
batch.printmessage("end of batch #2")
print("executing batch, there will be no result values. Check server to see printed messages...")
result = batch(oneway=True)  # execute the batch of remote calls, oneway, will return None
assert result is None
duration = time.time() - begin
print("total time taken {0:.2f} seconds ({1:.0f} calls/sec)".format(duration, NUMBER_OF_LOOPS * 2.0 / duration // 100 * 100))
print("oneway batched calls were {0:.1f} times faster than normal remote calls".format(duration_normal / duration))

# Batches can be executed asynchronous as well
print("\nBatched remote calls, asynchronous...")
batch = Pyro4.batch(p)  # get a batched call proxy for 'p'
batch.printmessage("beginning batch #3")
batch.multiply(7, 6)  # queue a call, note that it returns 'None' immediately
batch.add(10, 20)  # queue a call, note that it returns 'None' immediately
batch.delay(2)  # queue a delay, but this doesn't matter with asynchronous proxy
batch.printmessage("end of batch #3")
print("executing the batch... (should return immediately because async)")
asyncresult = batch(asynchronous=True)  # execute the batch, asynchronously (return immediately)
print("processing the results...(should wait until async results become available)")
results = list(asyncresult.value)
print("results=", results)


# Show what happens when one of the methods in a batch generates an error.
# (the batch is aborted and the error is raised locally again).
# Btw, you can re-use a batch proxy once you've called it and processed the results.
print("\nBatch with an error. Dividing a number by decreasing divisors...")
for d in range(3, -3, -1):  # divide by 3,2,1,0,-1,-2,-3... but 0 will be a problem ;-)
    batch.divide(100, d)
print("getting results...")
divisor = 3
try:
    for result in batch():
        print("100//%d = %d" % (divisor, result))
        divisor -= 1
        # this will raise the proper zerodivision exception once we're about
        # to process the batch result from the divide by 0 call.
except ZeroDivisionError:
    print("A divide by zero error occurred during the batch! (expected)")
    print("".join(getPyroTraceback()))
