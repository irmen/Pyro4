``Pyro4.config`` --- Configuration items
========================================

Pyro's configuration is available in the ``Pyro4.config`` object.
Detailed information about the API of this object is available in the :doc:`config` chapter.

.. note:: creation of the ``Pyro4.config`` object

  This object is constructed when you import Pyro4.
  It is an instance of the :class:`Pyro4.configuration.Configuration` class.
  The package initializer code creates it and the initial configuration is
  determined (from defaults and environment variable settings).
  It is then assigned to ``Pyro4.config``.

