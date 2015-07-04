"""
Tests for the package structure and import names.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import unittest
import Pyro4
import Pyro4.constants
import Pyro4.core
import Pyro4.errors
import Pyro4.naming
import Pyro4.nsc
import Pyro4.socketutil
import Pyro4.threadutil
import Pyro4.util


class TestPackage(unittest.TestCase):
    def testPyro4(self):
        self.assertIs(Pyro4.core.Daemon, Pyro4.Daemon)
        self.assertIs(Pyro4.core.Proxy, Pyro4.Proxy)
        self.assertIs(Pyro4.core.URI, Pyro4.URI)
        self.assertIs(Pyro4.core.callback, Pyro4.callback)
        self.assertIs(Pyro4.core.oneway, Pyro4.oneway)
        self.assertIs(Pyro4.core.async, Pyro4.async)
        self.assertIs(Pyro4.core.batch, Pyro4.batch)
        self.assertIs(Pyro4.naming.locateNS, Pyro4.locateNS)
        self.assertIs(Pyro4.naming.resolve, Pyro4.resolve)


if __name__ == "__main__":
    unittest.main()
