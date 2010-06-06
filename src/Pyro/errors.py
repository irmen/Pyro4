"""
Exception definitions.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong.
irmen@razorvine.net - http://www.razorvine.net/python/Pyro
"""

class PyroError(Exception):
    pass
class CommunicationError(PyroError):
    pass
class ConnectionClosedError(CommunicationError):
    pass
class TimeoutError(CommunicationError):
    pass
class ProtocolError(CommunicationError):
    pass
class NamingError(PyroError):
    pass
class DaemonError(PyroError):
    pass

