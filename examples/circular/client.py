import Pyro4

obj=Pyro4.core.Proxy("PYRONAME:example.chain.A")
print "Result=",obj.process(["hello"])
