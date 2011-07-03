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
                  +-- ProtocolError
                  +-- TimeoutError
                         |
                         +-- AsyncResultTimeout

.. automodule:: Pyro4.errors
   :members:
