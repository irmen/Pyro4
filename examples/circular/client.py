#!/usr/bin/env python

import Pyro

obj=Pyro.core.Proxy("PYRONAME:example.chain.A")
print("Result:")
print(obj.process(["hello"]))


