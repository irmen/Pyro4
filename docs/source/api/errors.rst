:mod:`Pyro4.errors` --- Exception classes
=========================================

The exception hierarchy is as follows::

    Exception
      |
      +-- PyroError
            |
            +-- NamingError
            +-- DaemonError
            +-- SecurityError
            +-- CommunicationError
                  |
                  +-- ConnectionClosedError
                  +-- TimeoutError
                  +-- ProtocolError
                          |
                          +-- SerializeError


.. automodule:: Pyro4.errors
   :members:
