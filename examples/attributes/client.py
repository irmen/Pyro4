from __future__ import print_function
import sys
import random
import Pyro4

if sys.version_info < (3, 0):
    input = raw_input


uri = input("enter attribute server object uri: ").strip()

with Pyro4.Proxy(uri) as p:

    # First do some normal method calls with and without a dotted path notation
    # to get at the sub-object. If the server is running with DOTTEDNAMES=False,
    # you will get attribute exceptions when trying to access methods with a
    # dotted attribute path. If DOTTEDNAMES=True on the server, it will work.
    # (however it is a security risk because it is possible to exploit object
    # traversal and obtain internal info of your server or execute arbitrary code).
    print("DOTTEDNAMES on the server is:", p.dottedNames())
    if p.dottedNames():
        print("Disabling METADATA on the client because DOTTEDNAMES is not compatible with that.")
        print("Note that DOTTEDNAMES is a deprecated feature that will be removed in the next version.")
        Pyro4.config.METADATA = False  # disable
    print("")
    value = p.getSubValue()
    print("value gotten from p.getSubValue()=", value)
    try:
        value = p.sub.getValue()
        print("value gotten from p.sub.getValue()=", value)
    except AttributeError:
        print("AttributeError occurred:", sys.exc_info()[1])
    print("adding 500 to the value")
    try:
        p.sub.addToValue(500)
    except AttributeError:
        print("AttributeError occurred:", sys.exc_info()[1])
    value = p.getSubValue()
    print("value gotten from p.getSubValue()=", value)
    try:
        value = p.sub.getValue()
        print("value gotten from p.sub.getValue()=", value)
    except AttributeError:
        print("AttributeError occurred:", sys.exc_info()[1])


# There is a SECURITY ISSUE when DOTTEDNAMES is enabled:
# client code can overwrite globals in the server by means of the object traversal exploit.
# (Similar to an old exploit of the xmlrpc lib: http://www.python.org/news/security/PSF-2005-001/ )
# Amongst other reasons, this is why the DOTTEDNAMES feature is now deprecated
# and why it will be removed in the next Pyro version.

Pyro4.config.METADATA = True  # make sure this setting is back to the default

with Pyro4.Proxy(uri) as p:
    print("\nattempt to do an object traversal exploit...")
    oldvalue = p.printSomething()
    try:
        # this update() call will work when the server has DOTTEDNAMES set to true...:
        p.printSomething.im_func.func_globals.update({"something": "J00 HAVE BEEN HAXX0RD! "+str(random.random())})
    except AttributeError:
        # this exception occurs when the server has DOTTEDNAMES set to false.
        print("Attributeerror occurred; couldn't update the server's global variable (allright!)")
    else:
        print("No attributeerror occurred; we have overwritten a global value in the server (haxx!)")
    newvalue = p.printSomething()
    if newvalue != oldvalue:
        print("The server has been exploited, a global variable has been updated with a different value:")
        print("Old value: {0}    new value: {1}".format(oldvalue, newvalue))

    # Direct remote attribute access.
    print("\nDirect attribute access:")
    print("p.prop_value=", p.prop_value)
    print("adding 500 to p.prop_value")
    p.prop_value += 500
    print("p.prop_value=", p.prop_value)
    print("actual remote value: ", p.getValue(), " (via p.getValue() remote method call)")
    if p.prop_value != p.getValue():
        # they differ!? (should not happen)
        print("Remote value is different! The p.prop_value attribute must be a local one (not remote), this should not happen! (because metadata is enabled here)")
    print()

    # dunder names
    print("calling p.__dunder__()....: ", p.__dunder__())

    # unexposed attributes
    try:
        print("accessing p.value...")
        _ = p.value
        raise RuntimeError("this should not be possible!")   # because p.value is not an exposed property
    except AttributeError as x:
        print("ok, got expected error:", x)
    try:
        print("accessing p._value...")
        _ = p._value
        raise RuntimeError("this should not be possible!")   # because p._value is private
    except AttributeError as x:
        print("ok, got expected error:", x)
    try:
        print("accessing p.__value...")
        _ = p.__value
        raise RuntimeError("this should not be possible!")   # because p.__value is private
    except AttributeError as x:
        print("ok, got expected error:", x)
