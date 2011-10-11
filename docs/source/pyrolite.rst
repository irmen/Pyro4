*******************************************
Pyrolite - client library for Java and .NET
*******************************************

This library allows your Java or .NET program to interface very easily with
the Python world. It uses the Pyro protocol to call methods on remote
objects. It also supports convenient access to a Pyro Flame server including the remote
interactive console.

Pyrolite only implements part of the client side Pyro library,
hence its name 'lite'...  Because Pyrolite has no dependencies,
it is a much lighter way to use Pyro from Java/.NET than a solution with
jython+pyro or IronPython+pyro would provide.
So if you don't need Pyro's full feature set, and don't require your
Java/.NET code to host Pyro objects itself, Pyrolite may be
a good choice to connect java or .NET and python.

Pyrolite contains an almost complete implementation of Python's :mod:`pickle` protocol
(with fairly intelligent mapping of datatypes between Python and Java/.NET),
and a small part of Pyro's client network protocol and proxy logic.

Small code example (java):

.. code-block:: java

    import net.razorvine.pyro.*;

    NameServerProxy ns = NameServerProxy.locateNS(null);
    PyroProxy something = new PyroProxy(ns.lookup("Your.Pyro.Object"));

    Object result = something.call("pythonmethod",42,"arguments",[1,2,3]);

    // depending on what 'pythonmethod' returns you'll have to cast
    // the result object to the appropriate type, such as HashMap for dicts, etc.

.. note::
  Pyrolite is very new and should be considered experimental.
  It does contain a large amount of unit tests to validate its behavior,
  but "be careful".

Get it from here: http://irmen.home.xs4all.nl/pyrolite/

Readme: http://irmen.home.xs4all.nl/pyrolite/README.txt

License (same as Pyro): http://irmen.home.xs4all.nl/pyrolite/LICENSE

Readonly subversion repository: :kbd:`svn://svn.razorvine.net/Various/Pyrolite`
