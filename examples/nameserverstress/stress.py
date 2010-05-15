#!/usr/bin/env python

import Pyro.naming
import random, time
from threading import Thread
from Pyro.errors import NamingError

mustStop=False

def randomname():
	def partname():
		return str(random.random())[-2:]
	parts=["stresstest"]
	for i in range(random.randint(1,10)):
		parts.append(partname())
	return ".".join(parts)
	

class NamingTrasher(Thread):
	def __init__(self,nsuri,number):
		Thread.__init__(self)
		self.daemon=True
		self.number=number
		self.ns=Pyro.core.Proxy(nsuri)

	def list(self):
		items=self.ns.list()
	def register(self):
		for i in range(4):
			try:
				self.ns.register(randomname(),'PYRO:objname@host:555')
			except NamingError:
				pass
	def remove(self):
		self.ns.remove(randomname())
	def lookup(self):
		try:
			uri=self.ns.lookup(randomname())
		except NamingError:
			pass
	def listprefix(self):
		entries=self.ns.list(prefix="stresstest.51")
	def listregex(self):
		entries=self.ns.list(regex=r"stresstest\.??\.41.*")
	def run(self):	
		print 'Name Server trasher running.'
		while not mustStop:
			random.choice((self.list, self.register, self.remove, self.lookup, self.listregex, self.listprefix)) ()
			print self.number,'called'
			time.sleep(random.random()/10)
		print 'Trasher exiting.'	

def main():
	threads=[]
	ns=Pyro.naming.locateNS()
	ns.remove(prefix="stresstest.")
	for i in range(10):
		nt=NamingTrasher(ns._pyroUri,i)
		nt.start()
		threads.append(nt)

	try:
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		pass

	mustStop=True
	print 'Break-- waiting for threads to stop.'
	for nt in threads:
		nt.join()
	ns.remove(prefix="stresstest.")

if __name__=='__main__':
	main()
