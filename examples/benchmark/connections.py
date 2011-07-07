from __future__ import print_function
import time, sys
import Pyro4

if sys.version_info<(3,0):
    input=raw_input

uri=input("Uri of benchmark server? ").strip()

print("Timing raw connect speed (no method call)...")
p=Pyro4.core.Proxy(uri)
p.ping()
ITERATIONS=2000
begin=time.time()
for loop in range(ITERATIONS):
    if loop%500==0:
        print(loop)
    p._pyroRelease()
    p._pyroBind()
duration=time.time()-begin
print("%d connections in %.3f sec = %.0f conn/sec" % (ITERATIONS, duration, ITERATIONS/duration))
del p

print("Timing proxy creation+connect+methodcall speed...")
ITERATIONS=2000
begin=time.time()
for loop in range(ITERATIONS):
    if loop%500==0:
        print(loop)
    with Pyro4.core.Proxy(uri) as p:
        p.ping()
duration=time.time()-begin
print("%d new proxy calls in %.3f sec = %.0f calls/sec" % (ITERATIONS, duration, ITERATIONS/duration))

print("Timing proxy methodcall speed...")
p=Pyro4.core.Proxy(uri)
p.ping()
ITERATIONS=10000
begin=time.time()
for loop in range(ITERATIONS):
    if loop%1000==0:
        print(loop)
    p.ping()
duration=time.time()-begin
print("%d calls in %.3f sec = %.0f calls/sec" % (ITERATIONS, duration, ITERATIONS/duration))
