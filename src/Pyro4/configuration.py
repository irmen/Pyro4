"""
Configuration settings.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

# Env vars used at package import time (see __init__.py):
# PYRO_LOGLEVEL   (enable Pyro log config and set level)
# PYRO_LOGFILE    (the name of the logfile if you don't like the default)

import os, sys


class Configuration(object):
    __slots__=("HOST", "NS_HOST", "NS_PORT", "NS_BCPORT", "NS_BCHOST",
               "COMPRESSION", "SERVERTYPE", "DOTTEDNAMES", "COMMTIMEOUT",
               "POLLTIMEOUT", "THREADING2", "ONEWAY_THREADED",
               "DETAILED_TRACEBACK", "SOCK_REUSE",
               "THREADPOOL_MINTHREADS", "THREADPOOL_MAXTHREADS",
               "THREADPOOL_IDLETIMEOUT", "HMAC_KEY", "AUTOPROXY",
               "BROADCAST_ADDRS", "NATHOST", "NATPORT")

    def __init__(self):
        self.reset()

    def reset(self, useenvironment=True):
        """
        Set default config items.
        If useenvironment is False, won't read environment variables settings (useful if you can't trust your env).
        """
        self.HOST = "localhost"  # don't expose us to the outside world by default
        self.NS_HOST = self.HOST
        self.NS_PORT = 9090      # tcp
        self.NS_BCPORT = 9091    # udp
        self.NS_BCHOST = None
        self.NATHOST = None
        self.NATPORT = 0
        self.COMPRESSION = False
        self.SERVERTYPE = "thread"
        self.DOTTEDNAMES = False   # server-side
        self.COMMTIMEOUT = 0.0
        self.POLLTIMEOUT = 2.0     # seconds
        self.SOCK_REUSE = False    # so_reuseaddr on server sockets?
        self.THREADING2 = False    # use threading2 if available?
        self.ONEWAY_THREADED = True     # oneway calls run in their own thread
        self.DETAILED_TRACEBACK = False
        self.THREADPOOL_MINTHREADS = 4
        self.THREADPOOL_MAXTHREADS = 50
        self.THREADPOOL_IDLETIMEOUT = 5.0
        self.HMAC_KEY = None   # must be bytes type
        self.AUTOPROXY = True
        self.BROADCAST_ADDRS = "<broadcast>, 0.0.0.0"   # comma separated list of broadcast addresses

        if useenvironment:
            # process enviroment variables
            PREFIX="PYRO_"
            for symbol in self.__slots__:
                if PREFIX+symbol in os.environ:
                    value=getattr(self,symbol)
                    envvalue=os.environ[PREFIX+symbol]
                    if value is not None:
                        valuetype=type(value)
                        if valuetype is bool:
                            # booleans are special
                            envvalue=envvalue.lower()
                            if envvalue in ("0", "off", "no", "false"):
                                envvalue=False
                            elif envvalue in ("1", "yes", "on", "true"):
                                envvalue=True
                            else:
                                raise ValueError("invalid boolean value: %s%s=%s" % (PREFIX, symbol, envvalue))
                        else:
                            envvalue=valuetype(envvalue)  # just cast the value to the appropriate type
                    setattr(self, symbol, envvalue)
        if self.HMAC_KEY and sys.version_info>=(3,0):
            if type(self.HMAC_KEY) is not bytes:
                self.HMAC_KEY=bytes(self.HMAC_KEY, "utf-8")     # convert to bytes

    def asDict(self):
        """returns the current config as a regular dictionary"""
        result={}
        for item in self.__slots__:
            result[item]=getattr(self,item)
        return result

    def parseAddressesString(self, addresses):
        """
        Parses the addresses string which contains one or more ip addresses separated by a comma.
        Returns a sequence of these addresses. '' is replaced by the empty string.
        """
        result=[]
        for addr in addresses.split(','):
            addr=addr.strip()
            if addr=="''":
                addr=""
            result.append(addr)
        return result

    def dump(self):
        # easy config diagnostics
        from Pyro4.constants import VERSION
        import inspect
        config=self.asDict()
        config["LOGFILE"]=os.environ.get("PYRO_LOGFILE")
        config["LOGLEVEL"]=os.environ.get("PYRO_LOGLEVEL")
        result= ["Pyro version: %s" % VERSION,
                 "Loaded from: %s" % os.path.abspath(os.path.split(inspect.getfile(Configuration))[0]),
                 "Active configuration settings:"]
        for n, v in sorted(config.items()):
            result.append("%s = %s" % (n, v))
        return "\n".join(result)

if __name__=="__main__":
    print(Configuration().dump())
