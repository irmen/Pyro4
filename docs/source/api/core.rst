:mod:`Pyro4.core` --- core Pyro logic
=====================================

.. automodule:: Pyro4.core
    :members: URI, Daemon, DaemonObject, callback, batch, async, Future, FutureResult

.. autoclass:: Proxy
    :members:

    .. py:attribute:: _pyroTimeout

        The timeout in seconds for calls on this proxy. Defaults to ``None``.
        If the timeout expires before the remote method call returns,
        Pyro will raise a :exc:`Pyro4.errors.TimeoutError`.

    .. py:attribute:: _pyroOneway

        A set of attribute names to be called as one-way method calls.
        This means the client won't wait for a response from the server
        while it is processing the call. Their return value is always ``None``.