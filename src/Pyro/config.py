"""
Pyro configuration settings.
"""

DEFAULT_SERVERHOST  =   "localhost"
DEFAULT_PORT        =   7766
DEFAULT_NS_PORT     =   9090
COMPRESSION         =   False   # XXX not used yet


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
