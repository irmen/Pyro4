#!/usr/bin/env python
import time
import Pyro

ns_uri=Pyro.naming.resolve("PYRONAME:Pyro.NameServer")
print("Name server location: %s"%ns_uri)

NUM_PROXIES=10  # 

print("Timing raw rebind (connect) speed... %d proxies"%NUM_PROXIES)
proxies=[Pyro.core.Proxy(ns_uri) for i in range(NUM_PROXIES)]
for p in proxies:
    p.ping()
begin=time.time()
ITERATIONS=150
for loop in range(ITERATIONS):
    if loop%25==0:
        print(loop*len(proxies))
    for p in proxies:
        p._pyroRelease()
        p._pyroBind()
duration=time.time()-begin
print("%d connections in %s sec = %f conn/sec" % (ITERATIONS*len(proxies), duration, ITERATIONS*len(proxies)/duration))
del proxies

print("Timing proxy connect speed...")
ITERATIONS=1500
begin=time.time()
for loop in range(ITERATIONS):
    if loop%250==0:
        print(loop)
    p=Pyro.core.Proxy(ns_uri)
    p.ping()
    p._pyroRelease()
duration=time.time()-begin
print("%d new proxy calls in %s sec = %f calls/sec" % (ITERATIONS, duration, ITERATIONS/duration))
