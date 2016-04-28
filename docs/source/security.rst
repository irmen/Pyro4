.. index:: security

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

.. index::
    double: security; pickle
    double: security; dill

Pickle and dill as serialization formats (optional)
===================================================
When configured to do so, Pyro is able to use the :py:mod:`pickle` module or the
:py:mod:`dill` module to serialize objects and then sends them over the network.
It is well known that using pickle or dill for this purpose is a security risk.
The main problem is that allowing a program to unpickle or undill arbitrary data
can cause arbitrary code execution and this may wreck or compromise your system.

Because of this, by default, a different serializer is used (serpent) that doesn't
have this security problem.
Some other means to enhance security are discussed below.

.. index::
    double: security; network interfaces

Network interface binding
=========================
By default Pyro binds every server on localhost, to avoid exposing things on a public network or over the internet by mistake.
If you want to expose your Pyro objects to anything other than localhost, you have to explicitly tell Pyro the
network interface address it should use. This means it is a conscious effort to expose Pyro objects to remote machines.

It is possible to tell Pyro the interface address by means of an environment variable or global config item (``HOST``).
In some situations, or if you're paranoid, it is advisable to override this setting in your server program
by setting the config item from within your own code instead of depending on an externally configured setting.


.. index::
    double: security; different user id

Running Pyro servers with different credentials/user id
=======================================================
The following is not a Pyro specific problem, but is important nonetheless:
If you want to run your Pyro server as a different user id or with different credentials as regular users,
*be very careful* what kind of Pyro objects you expose like this!

Treat this situation as if you're exposing your server on the internet (even when it's only running on localhost).
Keep in mind that it is still possible that a random user on the same machine connects to the local server.
You may need additional security measures to prevent random users from calling your Pyro objects.

.. index::
    double: security; encryption

Protocol encryption
===================
Pyro doesn't encrypt the data it sends over the network. This means you must not transfer
sensitive data on untrusted networks (especially user data, passwords, and such) because it is
possible to eavesdrop. Either encrypt the data yourself before passing it to Pyro, or run Pyro
over a secure network (VPN, ssl/ssh tunnel).


.. index::
    double: security; object traversal
    double: security; dotted names

Dotted names (object traversal)
===============================
Using dotted names on Pyro proxies (such as ``proxy.aaa.bbb.ccc()``) is not possible in Pyro, because it is a security vulnerability
(for similar reasons as described here http://www.python.org/news/security/PSF-2005-001/ ).


.. index::
    double: security; environment variables

Environment variables overriding config items
=============================================
Almost all config items can be overwritten by an environment variable.
If you can't trust the environment in which your script is running, it may be a good idea
to reset the config items to their default builtin values, without using any environment variables.
See :doc:`config` for the proper way to do this.


.. index::
    double: security; HMAC signature

Preventing arbitrary connections: HMAC signature
================================================
You can use a `HMAC signature <http://docs.python.org/library/hmac.html>`_ on every network transfer
to prevent malicious requests. The idea is to only have legit clients connect to your Pyro server.
Using the HMAC signature ensures that only clients with the correct secret key can create valid requests,
and that it is impossible to modify valid requests (even though the network data is not encrypted).
The hashing algorithm that is used in the HMAC is SHA-1.

You need to create and configure a secure shared key yourself.
The key is a byte string and must be cryptographically secure (there are various methods to create such a key).
Your server needs to set this key and every client that wants to connect to it also needs to
set it. You can set the shared key via the ``_pyroHmacKey`` property on a proxy or a daemon::

    daemon._pyroHmacKey = b"secretkey"
    proxy._pyroHmacKey = b"secretkey"


.. warning::
    It is hard to keep a shared secret key actually secret!
    People might read the source code of your software and extract the key from it.
    Pyro itself provides no facilities to help you with this, sorry.
    The Diffie-Hellman Key Exchange algorithm is ane example of a secure solution to this problem.
    There's the ``diffie-hellman`` example that shows the basics, but DO NOT use it directly
    as being "the secure way to do this" -- it's only demo code.
