from __future__ import print_function
import sys
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
        print("accessing p.sub...")
        _ = p.sub
        raise RuntimeError("this should not be possible!")   # because p.sub is not an exposed property
    except AttributeError as x:
        print("ok, got expected error:", x)
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
    # What will happen instead is that the first part of the name will be evaluated and returned,
    # and that the rest of the expression will be evaluated on the local object instead of
    # directly on the remote one.
    print("\nTrying dotted name traversal:")
    value = p.prop_sub
    print("value gotten from p.prop_sub=", value)
    print("\nTrying to update the dictionary directly on the remote object...")
    p.prop_sub.update({"test": "nope"})   # this will only update the local copy!
    new_value = p.prop_sub
    print("value gotten from p.prop_sub=", new_value, "  (should be unchanged!)")
    assert new_value == value, "update should not have been done remotely"
    try:
        print("\nTrying longer dotted name: p.prop_sub.foobar.attribute")
        _ = p.prop_sub.foobar.attribute
        raise RuntimeError("this should not be possible!")
    except Exception as x:
        remote_tb = getattr(x, "_pyroTraceback", None)
        if remote_tb:
            raise RuntimeError("We got a remote traceback but this should have been a local one only")
        print("ok, got expected error (local only):", x)
