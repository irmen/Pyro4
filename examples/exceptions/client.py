from __future__ import print_function
import sys

import Pyro4


test = Pyro4.core.Proxy("PYRONAME:example.exceptions")

print(test.div(2.0, 9.0))
try:
    print(2 // 0)
except ZeroDivisionError as x:
    print("DIVIDE BY ZERO: %s" % x)
try:
    print(test.div(2, 0))
except ZeroDivisionError as x:
    print("DIVIDE BY ZERO: %s" % x)
try:
    result = test.error()
    print("%r, %s" % (result, result))
except ValueError as x:
    print("VALUERROR: %s" % x)
try:
    result = test.error2()
    print("%r, %s" % (result, result))
except ValueError as x:
    print("VALUERROR: %s" % x)
try:
    result = test.othererr()
    print("%r, %s" % (result, result))
except Exception as x:
    print("ANOTHER ERROR: %s" % x)
try:
    result = test.unserializable()
    print("%r, %s" % (result, result))
except Exception as x:
    print("UNSERIALIZABLE ERROR: %s" % x)

print("\n*** invoking server method that crashes, catching traceback ***")
try:
    print(test.complexerror())
except Exception as x:
    print("CAUGHT ERROR  >>> %s" % x)
    print("Printing Pyro traceback >>>>>>")
    print("".join(Pyro4.util.getPyroTraceback()))
    print("<<<<<<< end of Pyro traceback")

print("\n*** installing pyro's excepthook")
sys.excepthook = Pyro4.util.excepthook
print("*** invoking server method that crashes, not catching anything ***")
print(test.complexerror())  # due to the excepthook, the exception will show the pyro error
