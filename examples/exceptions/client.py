import sys
import Pyro
from excep import MyError

test = Pyro.core.Proxy("PYRONAME:example.exceptions")

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

print("*** invoking server method that crashes, catching traceback ***")
try:
    print(test.complexerror())
except Exception:
    print("CAUGHT ERROR  >>> %s" % sys.exc_info()[1])
    print("Printing Pyro traceback >>>>>>")
    print("".join(Pyro.util.getPyroTraceback()))
    print("<<<<<<< end of Pyro traceback")
    
print("*** invoking server method that crashes, not catching anything ***")
print(test.complexerror())
