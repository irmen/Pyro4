.. index:: installing Pyro

***************
Installing Pyro
***************

This chapter will show how to obtain and install Pyro.

.. index::
    double: installing Pyro; requirements for Pyro

Requirements
------------
Pyro is written in 100% pure Python. It works on any recent operating system where a suitable Python implementation is available
(2.7, 3.3 and newer). It also works with Pypy and IronPython.
It will probably not work with Jython 2.7 at this time of writing. If you need this, try Pyro version 4.34 or older instead.
(if you only need to write *client* code in Jython/Java, consider using :doc:`pyrolite` instead!)


.. note::
    When Pyro is configured to use pickle, dill or marshal as its serialization format, it is required to have the same *major* Python versions
    on your clients and your servers. Otherwise the different parties cannot decipher each others serialized data.
    This means you cannot let Python 2.x talk to Python 3.x with Pyro. However
    it should be fine to have Python 3.3 talk to Python 3.4 for instance.
    The other protocols (serpent, json) don't have this limitation.


.. index::
    double: installing Pyro; obtaining Pyro

Obtaining and installing Pyro
-----------------------------

Pyro can be found on the Python package index: http://pypi.python.org/pypi/Pyro4/  (package name ``Pyro4``) and is
easily installed by typing ``pip install Pyro4`` at a command prompt.

**Anaconda** users can install the Pyro4 package from conda-forge using ``conda install -c conda-forge pyro4``.

You can also download the distribution archive (.tar.gz) from Pypi and run the ``setup.py`` script from that manually.

.. index:: serpent

.. note::
    The `serpent <https://pypi.python.org/pypi/serpent>`_ serialization library should be installed as a dependency.
    If you're using a version of Python older than 3.4, the `selectors34 <https://pypi.python.org/pypi/selectors34>`_
    backported module should also be installed as a dependency.
    Usually this happens automatically.

The source code is available on Github: https://github.com/irmen/Pyro4 and Serpent is there as well: https://github.com/irmen/Serpent


Stuff you get extra in the source distribution archive and not with packaged versions
-------------------------------------------------------------------------------------
If you decide to download the distribution (.tar.gz) you have a bunch of extras over installing Pyro directly.
It contains:

  docs/
    the Sphinx/RST sources for this manual
  examples/
    dozens of examples that demonstrate various Pyro features (highly recommended to examine these)
  tests/
    all unit tests
  src/
    The library source code (only this part is installed if you install the ``Pyro4`` package)
  and a couple of other files:
    a setup script and other miscellaneous files such as the license (see :doc:`license`).

If you don't want to download anything you can ofcourse view all of this online in the github repository as well.