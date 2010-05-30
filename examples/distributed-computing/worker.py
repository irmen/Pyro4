#!/usr/bin/env python
import os,socket,sys
from math import sqrt
try:
	import queue
except ImportError:
	import Queue as queue
import Pyro
from workitem import Workitem

WORKERNAME = "Worker_%d@%s" % (os.getpid(), socket.gethostname())

def factorize(n):
	"""simple algorithm to find the prime factorials of the given number n"""
	def isPrime(n):
		return not [x for x in range(2,int(sqrt(n))+1) if n%x == 0]
	primes = []
	candidates = range(2,int(n+1))
	candidate = 2
	while not primes and candidate in candidates:
		if n%candidate == 0 and isPrime(candidate):
			primes = primes + [candidate] + factorize(n/candidate)
		candidate += 1            
	return primes
    
def process(item):
	print("factorizing %s -->" % item.data)
	item.result=factorize(int(item.data))
	print(item.result)
	item.processedBy = WORKERNAME

def main():
	dispatcher = Pyro.core.Proxy("PYRONAME:example.distributed.dispatcher")
	print("This is worker %s" % WORKERNAME)
	print("getting work from dispatcher.")
	while True:
		try:
			item = dispatcher.getWork()
		except queue.Empty:
			print("no work available yet.")
		else:
			process(item)
			dispatcher.putResult(item)
			
if __name__=="__main__":
	main()
