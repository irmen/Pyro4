****************************************
Pyro - Python Remote Objects - |version|
****************************************

.. image:: _static/pyro-large.png
    :align: center
    :alt: PYRO logo

.. index:: what is Pyro

What is Pyro?
-------------
It is a library that enables you to build applications in which
objects can talk to each other over the network, with minimal programming effort.
You can just use normal Python method calls to call objects on other machines.
Pyro is a pure Python library and runs on many different platforms and Python versions.

Pyro is copyright © Irmen de Jong (irmen@razorvine.net | http://www.razorvine.net).  Please read :doc:`license`.

It's on Pypi as `Pyro4 <http://pypi.python.org/pypi/Pyro4/>`_.  Source on Github: https://github.com/irmen/Pyro4
and version 5 as `Pyro5 <http://pypi.python.org/pypi/Pyro5/>`__ (`Source <https://github.com/irmen/Pyro5>`__)


.. image:: _static/pyro5.png
    :align: right
    :width: 120px

Pyro4 is considered feature complete and new development is frozen.
Only very important bug fixes (such as security issues) will still be made to Pyro4.
New development, improvements and new features will only be available in its successor
`Pyro5 <https://pyro5.readthedocs.io/>`_ . New code should use Pyro5 unless a feature
of Pyro4 is strictly required.  Older code should consider migrating to Pyro5. It provides
a (simple) backwards compatibility api layer to make the porting easier.


.. toctree::
   :maxdepth: 2
   :caption: Contents of this manual:

   intro.rst
   install.rst
   tutorials.rst
   commandline.rst
   clientcode.rst
   servercode.rst
   nameserver.rst
   security.rst
   errors.rst
   flame.rst
   tipstricks.rst
   config.rst
   api.rst
   alternative.rst
   pyrolite.rst
   changelog.rst
   license.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`

.. figure:: _static/tf_pyrotaunt.png
   :target: http://wiki.teamfortress.com/wiki/Pyro
   :alt: PYYYRRRROOOO
   :align:  center
