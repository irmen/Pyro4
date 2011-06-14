from __future__ import print_function
import sys
import Pyro4
from excep import MyError

test = Pyro4.core.Proxy("PYRONAME:example.exceptions")

print(test.div(2.0,9.0))
try:
    print(2//0)
except ZeroDivisionError:
    print("DIVIDE BY ZERO: %s" % sys.exc_info()[1])
try:
    print(test.div(2,0))
except ZeroDivisionError:
    print("DIVIDE BY ZERO: %s" % sys.exc_info()[1])
try:
    result=test.error()
    print("%r, %s" % (result,result))
except ValueError:
    print("VALUERROR: %s" % sys.exc_info()[1])
try:
    result=test.error2()
    print("%r, %s" % (result,result))
except ValueError:
    print("VALUERROR: %s" % sys.exc_info()[1])
try:
    result=test.othererr()
    print("%r, %s" % (result,result))
except MyError:
    print("MYERROR: %s" % sys.exc_info()[1])
try:
    result=test.othererr2()
    print("%r, %s" % (result,result))
except MyError:
    print("MYERROR: %s" % sys.exc_info()[1])

print("\n*** invoking server method that crashes, catching traceback ***")
try:
    print(test.complexerror())
except Exception:
    print("CAUGHT ERROR  >>> %s" % sys.exc_info()[1])
    print("Printing Pyro traceback >>>>>>")
    print("".join(Pyro4.util.getPyroTraceback()))
    print("<<<<<<< end of Pyro traceback")

print("\n*** installing pyro's excepthook")
sys.excepthook=Pyro4.util.excepthook
print("*** invoking server method that crashes, not catching anything ***")
print(test.complexerror())     # due to the excepthook, the exception will show the pyro error

