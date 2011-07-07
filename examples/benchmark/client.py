from __future__ import print_function
import sys,time
import Pyro4
import bench

if sys.version_info<(3,0):
    input=raw_input

uri=input("Uri of benchmark server? ").strip()
object = Pyro4.core.Proxy(uri)
object._pyroOneway.add('oneway')
object._pyroBind()

def f1():
    _=object.length('Irmen de Jong')
def f2():
    _=object.timestwo(21)
def f3():
    _=object.bigreply()
def f4():
    _=object.manyargs(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15)
def f5():
    _=object.noreply(99993333)
def f6():
    _=object.varargs('een',2,(3,),[4])
def f7():
    _=object.keywords(arg1='zork')
def f8():
    _=object.echo('een',2,(3,),[4])
def f9():
    _=object.meth1('stringetje')
def fa():
    _=object.meth2('stringetje')
def fb():
    _=object.meth3('stringetje')
def fc():
    _=object.meth4('stringetje')
def fd():
    _=object.bigarg('Argument'*50)
def fe():
    object.oneway('stringetje',432423434)
def ff():
    _=object.mapping({"aap":42, "noot": 99, "mies": 987654})

funcs = (f1,f2,f3,f4,f5,f6,f7,f8,f9,fa,fb,fc,fd,fe,ff)

print('-------- BENCHMARK REMOTE OBJECT ---------')
print('Pay attention to the "fe" test -- this is a Oneway call and should be *fast*')
print('(if you are running the server and client on different machines)')
begin = time.time()
iters = 1000
for f in funcs:
    sys.stdout.write("%d times %s " % (iters,f.__name__))
    voor = time.time()
    for i in range(iters):
        f()
    sys.stdout.write("%.3f\n" % (time.time()-voor))
    sys.stdout.flush()
duration = time.time()-begin
print('total time %.3f seconds' % duration)
amount=len(funcs)*iters
print('total method calls: %d' % (amount))
avg_pyro_msec = 1000.0*duration/amount
print('avg. time per method call: %.3f msec (%d/sec)' % (avg_pyro_msec,amount/duration))

print('-------- BENCHMARK LOCAL OBJECT ---------')
object=bench.bench()
begin = time.time()
iters = 200000
for f in funcs:
    sys.stdout.write("%d times %s " % (iters,f.__name__))
    voor = time.time()
    for i in range(iters):
        f()
    sys.stdout.write("%.3f\n" % (time.time()-voor))
    sys.stdout.flush()
duration = time.time()-begin
print('total time %.3f seconds' % duration)
amount=len(funcs)*iters
print('total method calls: %d' % (amount))
avg_normal_msec = 1000.0*duration/amount
print('avg. time per method call: %.3f msec (%d/sec)' % (avg_normal_msec,amount/duration//1000*1000))
print('Normal method call is %.0f times faster than Pyro method call.'%(avg_pyro_msec/avg_normal_msec))
