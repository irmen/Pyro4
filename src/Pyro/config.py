"""
Configuration settings.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong.
irmen@razorvine.net - http://www.razorvine.net/python/Pyro
"""

HOST            =  "localhost"     # don't expose us to the outside world by default
NS_HOST         =  HOST
NS_PORT         =  9090     # tcp
NS_BCPORT       =  9091     # udp
NS_BCHOST       =  None
COMPRESSION     =  False
SERVERTYPE      =  "thread"
DOTTEDNAMES     =  False    # server-side 
COMMTIMEOUT     =  0.0
WORKERTHREADS   =  20       # 5 should be minimum
POLLTIMEOUT     =  2.0      # seconds
ONEWAY_THREADED    =  True     # oneway calls run in their own thread
DETAILED_TRACEBACK =  False
CONNECTHANDSHAKE = True     # should a connection handshake be done?
THREADING2      = False     # use threading2 if available?


# Btw, env vars only used at package import time (see __init__.py):
# PYRO_LOGLEVEL   (enable Pyro log config and set level)
# PYRO_LOGFILE    (the name of the logfile if you don't like the default)

def _process(dictionary):
    """Process all config items and update them with environment var settings if available."""
    import os, re
    PREFIX="PYRO_"
    rx=re.compile(r"[A-Z_]+[A-Z_0-9]*$")
    for symbol,value in dictionary.items():
        if rx.match(symbol):
            if PREFIX+symbol in os.environ:
                envvalue=os.environ[PREFIX+symbol]
                if value is not None:
                    valuetype=type(value)
                    if valuetype is bool:
                        # booleans are special
                        envvalue=envvalue.lower()
                        if envvalue in ("0","off","no","false"):
                            envvalue=False
                        elif envvalue in ("1","yes","on","true"):
                            envvalue=True
                        else:
                            raise ValueError("invalid boolean value: %s%s=%s" % (PREFIX, symbol, envvalue))
                    else:
                        envvalue=valuetype(envvalue)  # just cast the value to the appropriate type
                dictionary[symbol]=envvalue
 
_process(globals())
del _process

def asDict():
    """returns the current config as a regular dictionary"""
    import re
    rx=re.compile(r"[A-Z_]+[A-Z_0-9]*$")
    result={}
    for n,v in globals().items():
        if rx.match(n):
            result[n]=v
    return result
    
# easy config diagnostic with python -m
if __name__=="__main__":
    import Pyro.constants
    import os
    print "Pyro version:",Pyro.constants.VERSION
    print "Loaded from:",os.path.abspath(os.path.split(Pyro.__file__)[0])
    print "Active configuration settings:"
    for n,v in sorted(asDict().items()):
        print "%s=%s" % (n,v) 
