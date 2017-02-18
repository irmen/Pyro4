:mod:`Pyro4` --- Main API package
=================================

.. module:: Pyro4

:mod:`Pyro4` is the main package of Pyro4. It imports most of the other packages that it needs
and provides shortcuts to the most frequently used objects and functions from those packages.
This means you can mostly just ``import Pyro4`` in your code to start using Pyro.

The classes and functions provided are:

=================================== ==========================
symbol in :mod:`Pyro4`              referenced location
=================================== ==========================
.. py:data:: config                 the current configuration settings, :data:`Pyro4.configuration.config`
.. py:data:: current_context        the current client context, :data:`Pyro4.core.current_context`
.. py:class:: URI                   :class:`Pyro4.core.URI`
.. py:class:: Proxy                 :class:`Pyro4.core.Proxy`
.. py:class:: Daemon                :class:`Pyro4.core.Daemon`
.. py:class:: Future                :class:`Pyro4.futures.Future`
.. py:function:: callback           :func:`Pyro4.core.callback`
.. py:function:: batch              :func:`Pyro4.core.batch`
.. py:function:: async              :func:`Pyro4.core.async`
.. py:function:: locateNS           :func:`Pyro4.naming.locateNS`
.. py:function:: resolve            :func:`Pyro4.naming.resolve`
.. py:function:: expose             :func:`Pyro4.core.expose` (decorator ``@expose``)
.. py:function:: oneway             :func:`Pyro4.core.oneway` (decorator ``@oneway``)
.. py:function:: behavior           :func:`Pyro4.core.behavior` (decorator ``@behavior``)
=================================== ==========================


.. seealso::

   Module :mod:`Pyro4.core`
      The core Pyro classes and functions.

   Module :mod:`Pyro4.naming`
      The Pyro name server logic.
