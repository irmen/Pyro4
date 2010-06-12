import sys,os,time
import Pyro
import bench

object = Pyro.core.Proxy("PYRONAME:example.benchmark")
object._pyroOneway.add('oneway')
object._pyroBind()

def f1(): void=object.length('Irmen de Jong')
def f2(): void=object.timestwo(21)
def f3(): void=object.bigreply()
def f4(): void=object.manyargs(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15)
def f5(): void=object.noreply(99993333)
def f6(): void=object.varargs('een',2,(3,),[4])
def f7(): void=object.keywords(arg1='zork')
def f8(): void=object.echo('een',2,(3,),[4])
def f9(): void=object.meth1('stringetje')
def fa(): void=object.meth2('stringetje')
def fb(): void=object.meth3('stringetje')
def fc(): void=object.meth4('stringetje')
def fd(): void=object.bigarg('Argument'*50)
def fe(): void=object.oneway('stringetje',432423434)
def ff(): void=object.mapping( {"aap":42, "noot": 99, "mies": 987654} )

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
    sys.stdout.write("%.4f\n" % (time.time()-voor))
    sys.stdout.flush()
duration = time.time()-begin
print('total time %.4f seconds' % duration)
print('total method calls: %d' % (len(funcs)*iters))
avg_pyro_msec = 1000.0*duration/(len(funcs)*iters)
print('avg. time per method call: %.4f msec' % avg_pyro_msec)

print('-------- BENCHMARK LOCAL OBJECT ---------')
object=bench.bench()
begin = time.time()
iters = 200000
for f in funcs:
    sys.stdout.write("%d times %s " % (iters,f.__name__))
    voor = time.time()
    for i in range(iters):
        f()
    sys.stdout.write("%.4f\n" % (time.time()-voor))
    sys.stdout.flush()
duration = time.time()-begin
print('total time %.4f seconds' % duration)
print('total method calls: %d' % (len(funcs)*iters))
avg_normal_msec = 1000.0*duration/(len(funcs)*iters)
print('avg. time per method call: %.4f msec' % avg_normal_msec)
print('Normal method call is %.2f times faster than Pyro method call.'%(avg_pyro_msec/avg_normal_msec))
