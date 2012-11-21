.. _security:

********
Security
********

.. warning::
    Do not publish any Pyro objects to remote machines unless you've read and understood everything
    that is discussed in this chapter. This is also true when publishing Pyro objects with different
    credentials to other processes on the same machine.
    Why? In short: using Pyro has several security risks. Pyro has a few countermeasures to deal with them.
    Understanding the risks, the countermeasures, and their limits, is very important to avoid
    creating systems that are very easy to compromise by malicious entities.


Pickle as serialization format
==============================
Pyro uses the :py:mod:`pickle` module to serialize objects and then sends those pickles over the network.
It is well known that using pickle for this purpose is a security risk.
The main problem is that allowing a program to unpickle arbitrary data can cause arbitrary code execution
and this may wreck or compromise your system.

Although this may sound like a showstopper for using Pyro for anything serious, Pyro provides a few facilities
to deal with this security risk. They are discussed below.

Network interface binding
=========================
By default Pyro binds every server on localhost, to avoid exposing things on a public network or over the internet by mistake.
If you want to expose your Pyro objects to anything other than localhost, you have to explicitly tell Pyro the
network interface address it should use. This means it is a conscious effort to expose Pyro objects to remote machines.

It is possible to tell Pyro the interface address by means of an environment variable or global config item (``HOST``).
In some situations, or if you're paranoid, it is advisable to override this setting in your server program
by setting the config item from within your own code instead of depending on an externally configured setting.


Running Pyro servers with different credentials/user id
=======================================================
The following is not a Pyro specific problem, but is important nonetheless:
If you want to run your Pyro server as a different user id or with different credentials as regular users,
*be very careful* what kind of Pyro objects you expose like this!

Treat this situation as if you're exposing your server on the internet (even when it's only running on localhost).
Keep in mind that it is still possible that a random user on the same machine connects to the local server.
You may need additional security measures to prevent random users from calling your Pyro objects.


Protocol encryption
===================
Pyro doesn't encrypt the data it sends over the network. This means you must not transfer
sensitive data on untrusted networks (especially user data, passwords, and such) because it is
possible to eavesdrop. Either encrypt the data yourself before passing it to Pyro, or run Pyro
over a secure network (VPN, ssl/ssh tunnel).


Dotted names (object traversal)
===============================
Using dotted names on Pyro proxies (such as ``proxy.aaa.bbb.ccc()``)
is disallowed by default because it is a security vulnerability
(for similar reasons as described here http://www.python.org/news/security/PSF-2005-001/ ).
You can enable it with the ``DOTTEDNAMES`` config item, but be aware of the implications.

The :file:`attributes` example shows one of the exploits you can perform if it is enabled.


Environment variables overriding config items
=============================================
Almost all config items can be overwritten by an environment variable.
If you can't trust the environment in which your script is running, it may be a good idea
to reset the config items to their default builtin values, without using any environment variables.
See :doc:`config` for the proper way to do this.


Preventing arbitrary connections: HMAC signature
================================================
Pyro suggests using a `HMAC signature <http://docs.python.org/library/hmac.html>`_ on every network transfer
to prevent malicious requests. The idea is to only have legit clients connect to your Pyro server.
Using the HMAC signature ensures that only clients with the correct secret key can create valid requests,
and that it is impossible to modify valid requests (even though the network data is not encrypted).

You need to create and configure a secure shared key in the ``HMAC_KEY`` config item.
The key is a byte string and must be cryptographically secure (there are various methods to create such a key).
Your server needs to set this key and every client that wants to connect to it also needs to
set it.

Pyro will cause a Python-level warning message if you run it without a HMAC key, but it will run just fine.

.. warning::
    It is hard to keep a shared secret key actually secret!
    People might read the source code of your clients and extract the key from it.
    Pyro itself provides no facilities to help you with this, sorry.
