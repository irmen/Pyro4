from __future__ import print_function
import sys
import time
import Pyro4
import bench

Pyro4.config.SERIALIZER = "marshal"

if sys.version_info < (3, 0):
    input = raw_input

uri = input("Uri of benchmark server? ").strip()
obj = Pyro4.core.Proxy(uri)
obj._pyroBind()
assert "oneway" in obj._pyroOneway   # make sure this method is indeed marked as @oneway


funcs = [
    lambda: obj.length('Irmen de Jong'),
    lambda: obj.timestwo(21),
    lambda: obj.bigreply(),
    lambda: obj.manyargs(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15),
    lambda: obj.noreply([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
    lambda: obj.noreply(None),
    lambda: obj.varargs('een', 2, (3,), [4]),
    lambda: obj.keywords(arg1='zork'),
    lambda: obj.echo('een', 2, (3,), [4]),
    lambda: obj.echo({"aap": 42, "noot": 99, "mies": 987654}),
    lambda: obj.bigarg('Argument' * 50),
    lambda: obj.oneway('stringetje', 432423434, 9.8765432)
]

print('-------- BENCHMARK REMOTE OBJECT ---------')
begin = time.time()
iters = 1000
print("warmup...")
for _ in range(iters):
    funcs[0]()
for i, f in enumerate(funcs, start=1):
    print("call #%d, %d times... " % (i, iters), end="")
    before = time.time()
    for _ in range(iters):
        f()
    print("%.3f" % (time.time() - before))
duration = time.time() - begin
print('total time %.3f seconds' % duration)
amount = len(funcs) * iters
print('total method calls: %d' % amount)
avg_pyro_msec = 1000.0 * duration / amount
print('avg. time per method call: %.3f msec (%d/sec) (serializer: %s)' % (avg_pyro_msec, amount / duration, Pyro4.config.SERIALIZER))
