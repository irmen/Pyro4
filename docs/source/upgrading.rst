Upgrading from Pyro 3
*********************

Should I choose Pyro4?
======================

Should you use Pyro 4 or Pyro 3 for your project? This depends on a few things.

**Dependencies on older systems**

Pyro 4 has more modern system requirements than Pyro 3.
It is unsupported on Python versions below 2.6 (except Jython 2.5).
Pyro 3 runs fine on Python 2.5, and Pyro versions before 3.13 should run on even older Python versions.
So if you cannot use Python 2.6 or newer, you should use Pyro 3.

Pyro 4 has been written from scratch. While it looks and feels much like Pyro 3 did, its API and implementation are incompatible.
If you need to connect to existing systems that use Pyro 3, you can only do that with Pyro 3. Pyro 4 can't talk to them.

**Features**

Pyro 4 has several features that are not present in Pyro 3, but the reverse is also true.
If you require one of the following features for your system, you can only find them -for now- in Pyro 3:

- SSL support
- connection authentication
- mobile code
- remote attribute access
- Event server

Some of them may appear in the future in Pyro 4, but for now they're all exclusive to Pyro 3.

**Availability in package forms**

Some people can't or won't install software from source and rather use the package manager of their OS.
Pyro 4 is not yet available in Linux package managers. Pyro 3 is available as a Debian package (an older version, but still).
So if you are on Debian (or a derivative like Ubuntu or Mint) and you only accept software from the distribution packages,
Pyro 3 is your only choice for now.

**Maturity**

Pyro 3 has been around for many years and has a proven track record. It also has a very stable API.
It only gets bug fixes and much effort is taken to keep it backward compatible with previous 3.x versions.
Pyro 4 on the other hand is still under active development.
The important API parts are more or less stabilized but as features are being added or changed, stuff might break.
So depending on your requirements of maturity and API stability you might choose one or the other.

Differences
===========

*Here you can find what is different in Pyro4 compared to Pyro3.
This should help with converting existing Pyro3 applications to Pyro4.
It also serves as a quick overview for developers that are used to Pyro3,
to see what the new API and features of Pyro4 are like.*
