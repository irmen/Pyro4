
__all__=["CommunicationError","ConnectionClosedError","TimeoutError"]

class PyroError(Exception): pass

class CommunicationError(PyroError): pass
class ConnectionClosedError(CommunicationError): pass
class TimeoutError(CommunicationError): pass
class NamingError(PyroError): pass
