import Pyro.core

# a Chain member. Passes messages to the next link,
# until the message went full-circle: then it exits.

class Chain(object):
	def __init__(self, name, next):
		self.name=name
		self.nextName=next
		self.next=None
	def process(self,message):
		if self.next is None:
			self.next=Pyro.core.Proxy("PYRONAME:example.chain."+self.nextName)
		if self.name in message:
			print "Back at",self.name,"; we completed the circle!"
			return ["complete at "+self.name]
		else:
			print "I'm",self.name,", passing to ",self.nextName
			message.append(self.name)
			result=self.next.process(message)
			result.insert(0,"passed on from "+self.name)
			return result
