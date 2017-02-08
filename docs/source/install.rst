.. index:: installing Pyro

***************
Installing Pyro
***************

This chapter will show how to obtain and install Pyro.

.. index::
    double: installing Pyro; requirements for Pyro

Compatibility
-------------
Pyro is written in 100% pure Python. It works on any recent operating system where a suitable Python implementation is available
(2.7, 3.3 and newer). It also works with Pypy and IronPython.
It will probably not work with Jython 2.7 at this time of writing. If you need this, try Pyro version 4.34 or older instead.
(if you only need to write *client* code in Jython/Java, consider using :doc:`pyrolite` instead!)


.. note::
    When Pyro is configured to use pickle, dill or marshal as its serialization format, it is required to have the same *major* Python versions
    on your clients and your servers. Otherwise the different parties cannot decipher each others serialized data.
    This means you cannot let Python 2.x talk to Python 3.x with Pyro, when using those serializers.
    However it should be fine to have Python 3.3 talk to Python 3.4 for instance.
    The other protocols (serpent, json) don't have this limitation!


.. index::
    double: installing Pyro; obtaining Pyro

Obtaining and installing Pyro
-----------------------------

**Debian Linux (or Debian derived distributions)**
    You can install via the package manager: ``apt install python3-pyro4`` (for Python 3.x) or ``apt install python2-pyro4`` (for Python 2.x).
    Please pay attention to the packaged Pyro4 version, it can be quite old if you're not getting the package
    from the testing or unstable repositories.

**Anaconda**
    Anaconda users can install the Pyro4 package from conda-forge using ``conda install -c conda-forge pyro4``

**Pip**
    ``pip install Pyro4`` should do the trick.   Pyro is available `here <http://pypi.python.org/pypi/Pyro4/>`_  on pypi.

**Manual installation**
    Download the source distribution archive (Pyro4-X.YZ.tar.gz) from Pypi or Github, extract and ``python setup.py install``.
    The `serpent <https://pypi.python.org/pypi/serpent>`_ serialization library must also be installed.
    If you're using a version of Python older than 3.4, the `selectors34 <https://pypi.python.org/pypi/selectors34>`_
    backported module must also be installed to be able to use the multiplex server type.

**Github**
    Source is on Github: https://github.com/irmen/Pyro4
    The required serpent serializer library is there as well: https://github.com/irmen/Serpent


Stuff you get extra in the source distribution archive and not with packaged versions
-------------------------------------------------------------------------------------
If you decide to download the distribution (.tar.gz) you have a bunch of extras over simply installing the Pyro library directly.
It contains:

  docs/
    the Sphinx/RST sources for this manual
  examples/
    dozens of examples that demonstrate various Pyro features (highly recommended to examine these,
    many paragraphs in this manual refer to relevant examples here)
  tests/
    the unittest suite that checks for correctness and regressions
  src/
    The actual Pyro4 library's source code (only this part is installed if you install the ``Pyro4`` package)
  and a couple of other files:
    a setup script and other miscellaneous files such as the license (see :doc:`license`).

If you don't want to download anything, you can view all of this `online on Github <https://github.com/irmen/Pyro4>`_.