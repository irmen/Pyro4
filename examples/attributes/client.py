from __future__ import print_function
import sys
import random
import Pyro4

if sys.version_info < (3, 0):
    input = raw_input


uri = input("enter attribute server object uri: ").strip()


with Pyro4.Proxy(uri) as p:
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


with Pyro4.Proxy(uri) as p:
    # unexposed attributes
    print("\nAccessing unexposed attributes:")
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


with Pyro4.Proxy(uri) as p:
    # Dotted name traversal is not supported by Pyro because that is a security vulnerability.
    # Show that we get attribute errors if we try to do it anyway.
    print("\nTrying dotted name traversal:")
    value = p.getSubValue()
    print("value gotten from p.getSubValue()=", value)
    try:
        value = p.sub.getValue()
        print("value gotten from p.sub.getValue()=", value)
    except AttributeError as x:
        print("ok, got expected error:", x)
    print("adding 500 to the value")
    try:
        p.sub.addToValue(500)
    except AttributeError as x:
        print("ok, got expected error:", x)
    value = p.getSubValue()
    print("value gotten from p.getSubValue()=", value)
    try:
        value = p.sub.getValue()
        print("value gotten from p.sub.getValue()=", value)
    except AttributeError as x:
        print("ok, got expected error:", x)
