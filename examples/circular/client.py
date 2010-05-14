#!/usr/bin/env python

import Pyro.core

obj=Pyro.core.Proxy("PYRONAME:example.chain.A")
print "Result=",obj.process(["hello"])

