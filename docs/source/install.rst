***************
Installing Pyro
***************

This chapter will show how to obtain and install Pyro.

Requirements
------------
Short version: you need Python 2.6 or newer for Pyro4.

Longer version: Pyro4 is 'unsupported' on Python 2.5 or older (except Jython 2.5). This means it will probably work
on Python 2.5 (make sure by running the unit tests), but it's not supported for it. If at all possible, use
Python 2.6 or newer. Pyro4 will not work at all on anything older than Python 2.5.
Also see :ref:`should-i-choose-pyro4`.


Pyro is written in 100% pure Python, and has no other dependencies than a default Python installation.
It works on any recent operating system.

Obtaining and installing Pyro
-----------------------------

Pyro can be found on the Python package index: http://pypi.python.org/pypi/Pyro4/  (package name ``Pyro4``)

You can install it using :command:`pip` or :command:`easy_install`, or download the distribution archive (.tar.gz)
from Pypi and run the ``setup.py`` script from that manually.
Pyro installs as the ``Pyro4`` package with a couple of sub modules that you usually don't have to access directly.

.. note::
    Windows users: use one of the suggested tools to install Pyro.
    If you decide to get the distribution archive (.tar.gz) and use that,
    one way to extract it is to use the (free) `7-zip <http://www.7-zip.org>`_ archive utility.

Stuff you get in the distribution archive
-----------------------------------------
If you decide to download the distribution (.tar.gz) you have a bunch of extras over installing Pyro directly.
It contains:

  docs/
    the Sphinx/RST sources for this manual
  examples/
    dozens of examples that demonstrate various Pyro features (highly recommended)
  tests/
    all unit tests
  src/
    The library source code (only this part is installed if you install the ``Pyro4`` package)
  and a couple of other files:
    a setup script and other miscellaneous files such as the license (see :doc:`license`).
