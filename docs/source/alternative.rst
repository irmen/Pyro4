.. index:: alternative Python implementations

*********************************************
Running on alternative Python implementations
*********************************************

Pyro is written in 100% pure Python which -theoretically- enables it to be used with
any compatible Python implementation. There are a few gotchas however.
If possible please use the most recent version available of your Python implementation.

.. note::
    You may have to install the `serpent <https://pypi.python.org/pypi/serpent>`_ serialization library manually (this is a dependency).
    Check that you can ``import serpent`` to make sure it is installed.


.. index:: IronPython

IronPython
----------
`IronPython <http://ironpython.net>`_ is a Python implementation running on the .NET virtual machine.

- Pyro runs with IronPython 2.7.5. Older versions may or may not work, and can lack required modules such as zlib.

- IronPython cannot properly serialize exception objects, which could lead to problems when dealing with
  Pyro's enhanced tracebacks. For now, Pyro contains a workaround for this `bug <https://github.com/IronLanguages/main/issues/943>`_.

- You may have to use the ``-X:Frames`` command line option when starting Ironpython.
  (one of the libraries Pyro4 depends on when running in Ironpython, requires this)


.. index:: Pypy

Pypy
----
`Pypy <http://pypy.org>`_ is a Python implementation written in Python itself, and it usually
is quite a lot faster than the default implementation because it has a :abbr:`JIT (Just in time)`-compiler.

Pyro runs happily on recent versions of Pypy.
