######################################################################
#
#  Pyro configuration settings.
#
#  Pyro - Python Remote Objects.  Copyright by Irmen de Jong.
#  irmen@razorvine.net - http://www.razorvine.net/python/Pyro
#
######################################################################

import socket

HOST            =   socket.getfqdn()
NS_HOST         =   HOST
NS_PORT         =   9090    # tcp
NS_BCPORT       =   9091    # udp
NS_BCHOST       =   None
COMPRESSION     =   False
SERVERTYPE      =   "thread"
DOTTEDNAMES     =   False   # server-side 
COMMTIMEOUT     =   None
WORKER_THREADS  =   20       # 5 should be minimum
POLL_TIMEOUT    =   2        # seconds


# Btw, env vars only used at package import time (see __init__.py):
# PYRO_LOGLEVEL   (enable Pyro log config and set level)
# PYRO_LOGFILE    (the name of the logfile if you don't like the default)

def _process(dictionary):
    """Process all config items and update them with environment var settings if available."""
    import os, re
    PREFIX="PYRO_"
    rx=re.compile(r"[A-Z_]+$")
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
del socket


# easy config diagnostic with python -m
if __name__=="__main__":
    import Pyro.constants
    import re
    print "Pyro version:",Pyro.constants.VERSION
    print "Active configuration settings:"
    rx=re.compile(r"[A-Z_]+$")
    for n,v in globals().items():
        if rx.match(n):
            print "%s=%s" % (n,v)
