"""
Configuration settings.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

# Env vars used at package import time (see __init__.py):
# PYRO_LOGLEVEL   (enable Pyro log config and set level)
# PYRO_LOGFILE    (the name of the logfile if you don't like the default)

import os
import platform
import pickle
import socket
import Pyro4.constants


class Configuration(object):
    __slots__ = ("HOST", "NS_HOST", "NS_PORT", "NS_BCPORT", "NS_BCHOST", "NS_AUTOCLEAN",
                 "COMPRESSION", "SERVERTYPE", "COMMTIMEOUT",
                 "POLLTIMEOUT", "THREADING2", "ONEWAY_THREADED",
                 "DETAILED_TRACEBACK", "SOCK_REUSE", "SOCK_NODELAY", "PREFER_IP_VERSION",
                 "THREADPOOL_SIZE", "THREADPOOL_SIZE_MIN", "AUTOPROXY", "PICKLE_PROTOCOL_VERSION",
                 "BROADCAST_ADDRS", "NATHOST", "NATPORT", "MAX_MESSAGE_SIZE",
                 "FLAME_ENABLED", "SERIALIZER", "SERIALIZERS_ACCEPTED", "LOGWIRE",
                 "METADATA", "REQUIRE_EXPOSE", "USE_MSG_WAITALL", "JSON_MODULE",
                 "MAX_RETRIES", "DILL_PROTOCOL_VERSION", "ITER_STREAMING", "ITER_STREAM_LIFETIME",
                 "ITER_STREAM_LINGER")

    def __init__(self):
        self.reset()

    def reset(self, useenvironment=True):
        """
        Set default config items.
        If useenvironment is False, won't read environment variables settings (useful if you can't trust your env).
        """
        self.HOST = "localhost"  # don't expose us to the outside world by default
        self.NS_HOST = self.HOST
        self.NS_PORT = 9090  # tcp
        self.NS_BCPORT = 9091  # udp
        self.NS_BCHOST = None
        self.NS_AUTOCLEAN = 0.0
        self.NATHOST = None
        self.NATPORT = 0
        self.COMPRESSION = False
        self.SERVERTYPE = "thread"
        self.COMMTIMEOUT = 0.0
        self.POLLTIMEOUT = 2.0  # seconds
        self.SOCK_REUSE = True  # so_reuseaddr on server sockets?
        self.SOCK_NODELAY = False  # tcp_nodelay on socket?
        self.THREADING2 = False  # use threading2 if available?
        self.ONEWAY_THREADED = True  # oneway calls run in their own thread
        self.DETAILED_TRACEBACK = False
        self.THREADPOOL_SIZE = 40
        self.THREADPOOL_SIZE_MIN = 4
        self.AUTOPROXY = True
        self.MAX_MESSAGE_SIZE = 0  # 0 = unlimited
        self.BROADCAST_ADDRS = "<broadcast>, 0.0.0.0"  # comma separated list of broadcast addresses
        self.FLAME_ENABLED = False
        self.PREFER_IP_VERSION = 4  # 4, 6 or 0 (let OS choose according to RFC 3484)
        self.SERIALIZER = "serpent"
        self.SERIALIZERS_ACCEPTED = "serpent,marshal,json"   # these are the 'safe' serializers
        self.LOGWIRE = False  # log wire-level messages
        self.PICKLE_PROTOCOL_VERSION = pickle.HIGHEST_PROTOCOL
        try:
            import platform
            if platform.python_implementation() in ('PyPy', 'IronPython'):
                raise ImportError('Currently dill is not supported with PyPy and IronPython')
            import dill
            self.DILL_PROTOCOL_VERSION = dill.HIGHEST_PROTOCOL  # Highest protocol
        except ImportError:
            self.DILL_PROTOCOL_VERSION = -1
        self.METADATA = True  # get metadata from server on proxy connect
        self.REQUIRE_EXPOSE = True  # require @expose to make members remotely accessible (if False, everything is accessible)
        self.USE_MSG_WAITALL = hasattr(socket, "MSG_WAITALL") and platform.system() != "Windows"      # not reliable on windows even though it is defined
        self.JSON_MODULE = "json"
        self.MAX_RETRIES = 0
        self.ITER_STREAMING = True
        self.ITER_STREAM_LIFETIME = 0.0
        self.ITER_STREAM_LINGER = 30.0

        if useenvironment:
            # process environment variables
            PREFIX = "PYRO_"
            for symbol in self.__slots__:
                if PREFIX + symbol in os.environ:
                    value = getattr(self, symbol)
                    envvalue = os.environ[PREFIX + symbol]
                    if value is not None:
                        valuetype = type(value)
                        if valuetype is bool:
                            # booleans are special
                            envvalue = envvalue.lower()
                            if envvalue in ("0", "off", "no", "false"):
                                envvalue = False
                            elif envvalue in ("1", "yes", "on", "true"):
                                envvalue = True
                            else:
                                raise ValueError("invalid boolean value: %s%s=%s" % (PREFIX, symbol, envvalue))
                        else:
                            envvalue = valuetype(envvalue)  # just cast the value to the appropriate type
                    setattr(self, symbol, envvalue)

        self.SERIALIZERS_ACCEPTED = set(self.SERIALIZERS_ACCEPTED.split(','))

    def asDict(self):
        """returns the current config as a regular dictionary"""
        result = {}
        for item in self.__slots__:
            result[item] = getattr(self, item)
        return result

    def parseAddressesString(self, addresses):
        """
        Parses the addresses string which contains one or more ip addresses separated by a comma.
        Returns a sequence of these addresses. '' is replaced by the empty string.
        """
        result = []
        for addr in addresses.split(','):
            addr = addr.strip()
            if addr == "''":
                addr = ""
            result.append(addr)
        return result

    def dump(self):
        # easy config diagnostics
        from Pyro4.constants import VERSION
        import inspect
        if hasattr(platform, "python_implementation"):
            implementation = platform.python_implementation()
        else:
            implementation = "???"
        config = self.asDict()
        config["LOGFILE"] = os.environ.get("PYRO_LOGFILE")
        config["LOGLEVEL"] = os.environ.get("PYRO_LOGLEVEL")
        result = ["Pyro version: %s" % VERSION,
                  "Loaded from: %s" % os.path.abspath(os.path.split(inspect.getfile(Configuration))[0]),
                  "Python version: %s %s (%s, %s)" % (implementation, platform.python_version(), platform.system(), os.name),
                  "Protocol version: %d" % Pyro4.constants.PROTOCOL_VERSION,
                  "Currently active configuration settings:"]
        for n, v in sorted(config.items()):
            result.append("%s = %s" % (n, v))
        return "\n".join(result)


def configuration_dump():
    print(Configuration().dump())


if __name__ == "__main__":
    configuration_dump()
