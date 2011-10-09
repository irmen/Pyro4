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
.. py:class:: Pyro4.URI             :class:`Pyro4.core.URI`
.. py:class:: Pyro4.Proxy           :class:`Pyro4.core.Proxy`
.. py:class:: Pyro4.Daemon          :class:`Pyro4.core.Daemon`
.. py:class:: Pyro4.Future          :func:`Pyro4.core.Future`
.. py:function:: Pyro4.callback     :func:`Pyro4.core.callback`
.. py:function:: Pyro4.batch        :func:`Pyro4.core.batch`
.. py:function:: Pyro4.async        :func:`Pyro4.core.async`
.. py:function:: Pyro4.locateNS     :func:`Pyro4.naming.locateNS`
.. py:function:: Pyro4.resolve      :func:`Pyro4.naming.resolve`
=================================== ==========================


.. seealso::

   Module :mod:`Pyro4.core`
      The core Pyro classes and functions.

   Module :mod:`Pyro4.naming`
      The Pyro name server logic.
