import Pyro

obj=Pyro.core.Proxy("PYRONAME:example.chain.A")
print("Result=%s" % obj.process(["hello"]))
