Installing Pyro
***************

This chapter will show how to obtain and install Pyro.

Obtaining and installing Pyro
-----------------------------

Pyro can be found on the Python package index: http://pypi.python.org/pypi/Pyro4/  (package name ``Pyro4``)

You can install it using :command:`pip` or :command:`easy_install`, or download the distribution archive (.tar.gz)
from Pypi and run the ``setup.py`` script from that manually.
Pyro installs as the ``Pyro4`` package with a couple of sub modules that you usually don't have to access directly.

Contents of the distribution archive
------------------------------------
If you decide to download the distribution (.tar.gz) you have a few extras over installing Pyro directly.
It contains:

  docs/
    the Sphinx/RST sources for this manual
  examples/
    dozens of examples that demonstrate various Pyro features (highly recommended)
  tests/
    all unit tests
  src/
    The library source code (this part is installed if you install the ``Pyro4`` package)
  and a couple of other files:
    a setup script and other miscellaneous files such as the license (see :doc:`license`).
