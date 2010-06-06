import time
import Pyro

class RemoteObject(object):
	def __init__(self):
		self.amount=0
	def method(self, arg):
		return " ~~this is the remote result~~ "
	def work(self):
		print "work...",self.amount
		time.sleep(0.5)
		self.amount+=1
	def reset_work(self):
		self.amount=0
	def get_work_done(self):
		return self.amount

ns=Pyro.naming.locateNS()
daemon=Pyro.core.Daemon()
obj=RemoteObject()
uri=daemon.register(obj)
ns.remove("example.proxysharing")
ns.register("example.proxysharing", uri)
print "Server is ready."
daemon.requestLoop()
