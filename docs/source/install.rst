.. index:: installing Pyro

***************
Installing Pyro
***************

This chapter will show how to obtain and install Pyro.

Pyro5
-----

.. image:: _static/pyro5.png
    :align: right
    :width: 120px

Pyro4 is considered feature complete and new development is frozen.
Only very important bug fixes (such as security issues) will still be made to Pyro4.
New development, improvements and new features will only be available in its successor
`Pyro5 <https://pyro5.readthedocs.io/>`_ . New code should use Pyro5 unless a feature
of Pyro4 is strictly required.  Older code should consider migrating to Pyro5. It provides
a (simple) backwards compatibility api layer to make the porting easier.



.. index::
    double: installing Pyro; requirements for Pyro

Compatibility
-------------
Pyro4 is written in 100% Python. It works on any recent operating system where a suitable supported Python implementation is available
(2.7, or 3.5 and newer). It also works with Pypy (2 and 3). Maybe it also works with other Python implementations, but those are not tested.
(if you only need to write *client* code in Jython/Java, consider using :doc:`pyrolite` instead!)


.. note::
    When Pyro is configured to use pickle, cloudpickle, dill or marshal as its serialization format, it is required to have the same
    *major* Python versions on your clients and your servers. Otherwise the different parties cannot decipher each others serialized data.
    This means you cannot let Python 2.x talk to Python 3.x with Pyro, when using those serializers.
    However it should be fine to have Python 3.5 talk to Python 3.6 for instance.
    The other protocols (serpent, json) don't have this limitation!


.. index::
    double: installing Pyro; obtaining Pyro

Obtaining and installing Pyro
-----------------------------

**Linux**
    Some Linux distributions offer Pyro4 through their package manager. Make sure you install the correct
    one for the python version that you are using. It may be more convenient to just pip install it instead
    in a virtualenv.

**Anaconda**
    Anaconda users can install the Pyro4 package from conda-forge using ``conda install -c conda-forge pyro4``

**Pip install**
    ``pip install Pyro4`` should do the trick.   Pyro is available `here <http://pypi.python.org/pypi/Pyro4/>`_  on pypi.

**Manual installation from source**
    Download the source distribution archive (Pyro4-X.YZ.tar.gz) from Pypi or Github, extract and ``python setup.py install``.
    The `serpent <https://pypi.python.org/pypi/serpent>`_ serialization library must also be installed.
    If you're using a version of Python older than 3.5, the `selectors2 <https://pypi.python.org/pypi/selectors2>`_
    or `selectors34 <https://pypi.python.org/pypi/selectors34>`_  backported module must also be installed
    to be able to use the multiplex server type.

**Github**
    Source is on Github: https://github.com/irmen/Pyro4
    The required serpent serializer library is there as well: https://github.com/irmen/Serpent


Third party libraries that Pyro4 uses
-------------------------------------

`serpent <https://pypi.python.org/pypi/serpent>`_ - required
    Should be installed automatically when you install Pyro4.

`selectors34 <https://pypi.python.org/pypi/selectors34>`_ - required on Python 3.3 or older
    Should be installed automatically when you install Pyro4.

`selectors2 <https://pypi.python.org/pypi/selectors2>`_ - optional on Python 3.4 or older
    Install this if you want better behavior for interrupted system calls on Python 3.4 or older.

`dill <https://pypi.python.org/pypi/dill>`_ - optional
    Install this if you want to use the dill serializer.

`cloudpickle <https://pypi.python.org/pypi/cloudpickle>`_ - optional
    Install this if you want to use the cloudpickle serializer.

`msgpack <https://pypi.python.org/pypi/msgpack>`_ - optional
    Install this if you want to use the msgpack serializer.


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
