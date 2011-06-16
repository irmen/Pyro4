Intro and sample
****************

About Pyro
==========

Pyro is written in 100% pure Python and therefore runs on many platforms and Python versions:

* Python 2.6, 2.7, 3.2
* IronPython, Jython and Pypy
* 32-bit and 64-bit architectures
* Windows, Linux, Mac OS, in fact: every OS that has a suitable Python version.

You can often mix these as you please.

Features
========

Very fast overview of all the features Pyro provides:

- written in 100% Python so extremely portable.
- support for all Python datatypes that are pickleable.
- runs in normal CPython 2.x, CPython 3.x, IronPython, jython. Not tested with Pypy yet.
- works between systems on different architectures (64-bit, 32-bit, Intel, PowerPC...)
- designed to be very easy to use and get out of your way as much as possible.
- remote exceptions will be raised in the caller, as if they were local. You can extract detailed remote traceback information.
- name server that keeps track of your object's actual locations so you can move them around transparently.
- support for automatic reconnection to servers in case of interruptions.
- one-way invocations for enhanced performance.
- batched invocations for greatly enhanced performance of many calls on the same object.
- many simple examples included to show various features and techniques.
- large amount of unit tests and fairly high test coverage.
- built upon more than 10 years of previous Pyro versions.
- stable and heavily tested network communication code that works reliably on many platforms.



Stuff that needs to be here as well
-----------------------------------

Introduce the basic Pyro features by means of a VERY simple example.
Really simple because the tutorial covers an extensive example.
Describe the setup of a simple example (server, client, using nameserver).
Show how to do it without a name server.
Little bit of history? (how Pyro came to be, Pyro 3, Pyro4)   

