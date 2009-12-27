"""
Pyro exceptions.
"""
class PyroError(Exception): pass

class CommunicationError(PyroError): pass
class ConnectionClosedError(CommunicationError): pass
class TimeoutError(CommunicationError): pass
class ProtocolError(CommunicationError): pass
class NamingError(PyroError): pass
class DaemonError(PyroError): pass

