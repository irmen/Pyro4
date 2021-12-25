[![Latest Version](https://img.shields.io/pypi/v/Pyro4.svg)](https://pypi.python.org/pypi/Pyro4/)
[![Anaconda-Server Badge](https://anaconda.org/conda-forge/pyro4/badges/version.svg)](https://anaconda.org/conda-forge/pyro4)

PYRO - Python Remote Objects
============================

Pyro enables you to build applications in which objects can talk
to each other over the network, with minimal programming effort.
You can just use normal Python method calls to call objects on
other machines. Pyro is a pure Python library so it
runs on many different platforms and Python versions.


This software is copyright (c) by Irmen de Jong (irmen@razorvine.net).

This software is released under the MIT software license.
This license, including disclaimer, is available in the 'LICENSE' file.

Pyro5
-----
Pyro4 is considered feature complete and new development is frozen.
Only very important bug fixes (such as security issues) will still be made to Pyro4.
New development, improvements and new features will only be available in its successor
Pyro5: https://pyro5.readthedocs.io New code should strongly consider using Pyro5 unless a feature
of Pyro4 is strictly required.  Older code should consider migrating to Pyro5. It provides
a (simple) backwards compatibility api layer to make the porting easier.

Documentation
=============
Documentation can be found online at: http://pyro4.readthedocs.io
(or unformatted here in the repo at: docs/source/intro.rst)


Feature overview
================

Pyro is a library that enables you to build applications in which
objects can talk to each other over the network, with minimal programming effort.
You can just use normal Python method calls, with almost every possible parameter
and return value type, and Pyro takes care of locating the right object on the right
computer to execute the method. It is designed to be very easy to use, and to
generally stay out of your way. But it also provides a set of powerful features that
enables you to build distributed applications rapidly and effortlessly.
Pyro is a pure Python library and runs on many different platforms and Python versions.

Here's a quick overview of Pyro's features:

- written in 100% Python so extremely portable, runs on Python 2.7, Python 3.5 and newer, IronPython, Pypy 2 and 3.
- works between different system architectures and operating systems.
- able to communicate between different Python versions transparently.
- defaults to a safe serializer (serpent https://pypi.python.org/pypi/serpent ) that supports many Python data types.
- supports different serializers (serpent, json, marshal, msgpack, pickle, cloudpickle, dill).
- can use IPv4, IPv6 and Unix domain sockets.
- optional secure connections via SSL/TLS (encryption, authentication and integrity), including certificate validation on both ends (2-way ssl).
- lightweight client library available for .NET and Java native code ('Pyrolite', provided separately).
- designed to be very easy to use and get out of your way as much as possible, but still provide a lot of flexibility when you do need it.
- name server that keeps track of your object's actual locations so you can move them around transparently.
- yellow-pages type lookups possible, based on metadata tags on registrations in the name server.
- support for automatic reconnection to servers in case of interruptions.
- automatic proxy-ing of Pyro objects which means you can return references to remote objects just as if it were normal objects.
- one-way invocations for enhanced performance.
- batched invocations for greatly enhanced performance of many calls on the same object.
- remote iterator on-demand item streaming avoids having to create large collections upfront and transfer them as a whole.
- you can define timeouts on network communications to prevent a call blocking forever if there's something wrong.
- asynchronous invocations if you want to get the results 'at some later moment in time'. Pyro will take care of gathering the result values in the background.
- remote exceptions will be raised in the caller, as if they were local. You can extract detailed remote traceback information.
- http gateway available for clients wanting to use http+json (such as browser scripts).
- stable network communication code that works reliably on many platforms.
- can hook onto existing sockets created for instance with socketpair() to communicate efficiently between threads or sub-processes.
- possibility to use Pyro's own event loop, or integrate it into your own (or third party) event loop.
- three different possible instance modes for your remote objects (singleton, one per session, one per call).
- many simple examples included to show various features and techniques.
- large amount of unit tests and high test coverage.
- reliable and established: built upon more than 15 years of existing Pyro history, with ongoing support and development.
