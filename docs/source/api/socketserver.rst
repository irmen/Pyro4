Socket server API contract
**************************

For now, this is an internal API, used by the Pyro Daemon.
The various servers in Pyro4.socketserver implement this.

.. py:class:: SocketServer_API

    **Methods:**

    .. py:method:: init(daemon, host, port, unixsocket=None)

        Must bind the server on the given host and port (can be None).
        daemon is the object that will receive Pyro invocation calls (see below).
        When host or port is None, the server can select something appropriate itself.
        If possible, use ``Pyro4.config.COMMTIMEOUT`` on the sockets (see :doc:`config`).
        Set ``self.sock`` to the daemon server socket.
        If unixsocket is given the name of a Unix domain socket, that type of socket
        will be created instead of a regular tcp/ip socket.

    .. py:method:: loop(loopCondition)

        Start an endless loop that serves Pyro requests.
        loopCondition is an optional function that is called every iteration,
        if it returns False, the loop is terminated and this method returns.

    .. py:method:: events(eventsockets)

        Called from external event loops: let the server handle events that occur on one of the sockets of this server.
        eventsockets is a sequence of all the sockets for which an event occurred.

    .. py:method:: shutdown()

        Initiate shutdown of a running socket server, and close it.

    .. py:method:: close()

        Release resources and close a stopped server. It can no longer be used after calling this,
        until you call initServer again.

    .. py:method:: wakeup()

        This is called to wake up the :meth:`requestLoop` if it is in a blocking state.

    **Properties:**
    
    .. py:attribute:: sockets

        must be the list of all sockets used by this server (server socket + all connected client sockets)

    .. py:attribute:: sock

        must be the server socket itself.

    .. py:attribute:: locationStr

        must be a string of the form ``"serverhostname:serverport"``
        can be different from the host:port arguments passed to initServer.
        because either of those can be None and the server will choose something appropriate.
        If the socket is a Unix domain socket, it should be of the form ``"./u:socketname"``.
