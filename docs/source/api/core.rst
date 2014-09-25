:mod:`Pyro4.core` --- core Pyro logic
=====================================

.. automodule:: Pyro4.core
    :members: URI, Daemon, DaemonObject, callback, batch, async, expose, oneway

.. autoclass:: Proxy
    :members:

    .. py:attribute:: _pyroTimeout

        The timeout in seconds for calls on this proxy. Defaults to ``None``.
        If the timeout expires before the remote method call returns,
        Pyro will raise a :exc:`Pyro4.errors.TimeoutError`.

