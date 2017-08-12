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
    double: security; cloudpickle
    double: security; dill

Pickle, cloudpickle and dill as serialization formats (optional)
================================================================
When configured to do so, Pyro is able to use the :py:mod:`pickle`, :py:mod:`cloudpickle`
or :py:mod:`dill` modules to serialize objects and then sends them over the network.
It is well known that using these serializers for this purpose is a security risk.
The main problem is that allowing a program to deserialize this type of serialized data
can cause arbitrary code execution and this may wreck or compromise your system.
Because of this the default serializer is serpent, which doesn't have this security problem.
Some other means to enhance security are discussed below.

.. index::
    double: security; network interfaces

Network interface binding
=========================
By default Pyro binds every server on localhost, to avoid exposing things on a public network or over the internet by mistake.
If you want to expose your Pyro objects to anything other than localhost, you have to explicitly tell Pyro the
network interface address it should use. This means it is a conscious effort to expose Pyro objects to other machines.

It is possible to tell Pyro the interface address via an environment variable or global config item (``HOST``).
In some situations - or if you're paranoid - it is advisable to override this setting in your server program
by setting the config item from within your own code, instead of depending on an externally configured setting.


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

.. index:: SSL, TLS
    double: security; encryption

Secure communication via SSL/TLS
================================
Pyro itself doesn't encrypt the data it sends over the network. This means if you use the default
configuration, you must never transfer sensitive data on untrusted networks
(especially user data, passwords, and such) because eavesdropping is possible.

You can run Pyro over a secure network (VPN, ssl/ssh tunnel) where the encryption
is taken care of externally. It is also possible however to enable SSL/TLS in Pyro itself,
so that all communication is secured via this industry standard that
provides encryption, authentication, and anti-tampering (message integrity).

**Using SSL/TLS**

Enable it by setting the ``SSL`` config item to True, and configure the other SSL config items
as required. You'll need to specify the cert files to use, private keys, and passwords if any.
By default, the SSL mode only has a cert on the server (which is similar to visiting a https url
in your browser). This means your *clients* can be sure that they are connecting to the expected
server, but the *server* has no way to know what clients are connecting.
You can solve this by using a HMAC key (see :ref:`hmackey`), but if you're already using SSL,
a better way is to do custom certificate verification.
You can do this in your client (checks the server's cert) but you can also tell your clients
to use certs as well and check these in your server. This makes it 2-way-SSL or mutual authentication.
For more details see here :ref:`cert_verification`. The SSL config items are in :ref:`config-items`.

For example code on how to set up a 2-way-SSL Pyro client and server, with cert verification,
see the ``ssl`` example.

.. important::
    You must use at least Python 2.7.11 / 3.4.4 or newer for proper SSL support.

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

Preventing arbitrary connections
================================

.. _hmackey:

by using a HMAC signature via a shared private key
--------------------------------------------------

You can use a `HMAC signature <http://docs.python.org/library/hmac.html>`_ on every network transfer
to prevent malicious requests. The idea is to only have legit clients connect to your Pyro server.
Using the HMAC signature ensures that only clients with the correct secret key can create valid requests,
and that it is impossible to modify valid requests (even though the network data is not encrypted).
The hashing algorithm that is used in the HMAC is SHA-1.

.. sidebar:: consider alternatives

    For industry standard encryption and connection verification, consider using SSL/TLS instead.


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
    The Diffie-Hellman Key Exchange algorithm is one example of a secure solution to this problem.
    There's the ``diffie-hellman`` example that shows the basics, but DO NOT use it directly
    as being "the secure way to do this" -- it's only demo code.


.. index:: certificate verification, 2-way-SSL

.. _cert_verification:

by using 2-way-SSL and certificate verficiation
-----------------------------------------------

When using SSL, you should also do some custom certificate verification, such as checking the serial number
and commonName. This way your code is not only certain that the communication is encrypted, but also
that it is talking to the intended party and nobody else (middleman).
The server hostname and cert expiration dates *are* checked automatically, but
other attributes you have to verify yourself.

This is fairly easy to do: you can use :ref:`conn_handshake` for this. You can then get the peer certificate
using :py:meth:`Pyro4.socketutil.SocketConnection.getpeercert`.

If you configure a client cert as well as a server cert, you can/should also do verification of
client certificates in your server. This is a good way to be absolutely certain that you only
allow clients that you know and trust, because you can check the required unique certificate attributes.

Having certs on both client and server is called 2-way-SSL or mutual authentication.

The ``ssl`` example shows how to do this.
