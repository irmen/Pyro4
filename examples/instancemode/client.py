from __future__ import print_function
import Pyro4
import Pyro4.util
import sys

sys.excepthook = Pyro4.util.excepthook


print("Showing the different instancing modes.")
print("The number printed, is the id of the instance that handled the call.")

print("\n-----PERCALL-----")
with Pyro4.Proxy("PYRONAME:instance.percall") as p:
    print(p.msg("hello1"))
    print(p.msg("hello2"))
    print(p.msg("hello3"))

print("\n-----SESSION-----")
print("proxy 1...")
with Pyro4.Proxy("PYRONAME:instance.session") as p:
    print(p.msg("hello1"))
    print(p.msg("hello1"))
    print(p.msg("hello1"))
print("proxy 2...")
with Pyro4.Proxy("PYRONAME:instance.session") as p:
    print(p.msg("hello2"))
    print(p.msg("hello2"))
    print(p.msg("hello2"))
print("proxy 3...")
with Pyro4.Proxy("PYRONAME:instance.session") as p:
    print(p.msg("hello3"))
    print(p.msg("hello3"))
    print(p.msg("hello3"))

print("\n-----SINGLE-----")
with Pyro4.Proxy("PYRONAME:instance.single") as p:
    print(p.msg("hello1"))
    print(p.msg("hello1"))
    print(p.msg("hello1"))
with Pyro4.Proxy("PYRONAME:instance.single") as p:
    print(p.msg("hello2"))
    print(p.msg("hello2"))
    print(p.msg("hello2"))
with Pyro4.Proxy("PYRONAME:instance.single") as p:
    print(p.msg("hello3"))
    print(p.msg("hello3"))
    print(p.msg("hello3"))

print("\n-----OLDSTYLE-----")
with Pyro4.Proxy("PYRONAME:instance.oldstyle") as p:
    print(p.msg("hello1"))
with Pyro4.Proxy("PYRONAME:instance.oldstyle") as p:
    print(p.msg("hello2"))
with Pyro4.Proxy("PYRONAME:instance.oldstyle") as p:
    print(p.msg("hello3"))
