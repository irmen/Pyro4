"""
Tests for the package structure and import names.
Also checks if the key API functions are still in place.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import unittest

# this tests the __all__ definitions:
from Pyro4 import *
from Pyro4.configuration import *
from Pyro4.constants import *
from Pyro4.core import *
from Pyro4.errors import *
from Pyro4.futures import *
from Pyro4.message import *
from Pyro4.naming import *
from Pyro4.naming_storage import *
from Pyro4.nsc import *
from Pyro4.socketutil import *
from Pyro4.util import *
from Pyro4.socketserver.multiplexserver import *
from Pyro4.socketserver.threadpoolserver import *
from Pyro4.socketserver.threadpool import *
from Pyro4.test.echoserver import *
from Pyro4.utils.flame import *
from Pyro4.utils.flameserver import *
from Pyro4.utils.httpgateway import *

#regular imports:
import Pyro4.constants
import Pyro4.core
import Pyro4.errors
import Pyro4.naming
import Pyro4.nsc
import Pyro4.socketutil
import Pyro4.util


class TestPackage(unittest.TestCase):
    def testPyro4(self):
        self.assertIs(Pyro4.core.Daemon, Pyro4.Daemon)
        self.assertIs(Pyro4.core.Proxy, Pyro4.Proxy)
        self.assertIs(Pyro4.core.URI, Pyro4.URI)
        self.assertIs(Pyro4.core.callback, Pyro4.callback)
        self.assertIs(Pyro4.core.oneway, Pyro4.oneway)
        self.assertIs(Pyro4.core.asyncproxy, Pyro4.asyncproxy)
        self.assertIs(Pyro4.core.batch, Pyro4.batch)
        self.assertIs(Pyro4.core.expose, Pyro4.expose)
        self.assertIs(Pyro4.core.behavior, Pyro4.behavior)
        self.assertIs(Pyro4.core._locateNS, Pyro4.locateNS)
        self.assertIs(Pyro4.core._resolve, Pyro4.resolve)
        self.assertIs(Pyro4.core._locateNS, Pyro4.naming.locateNS, "old API function location must still be valid")
        self.assertIs(Pyro4.core._resolve, Pyro4.naming.resolve, "old API function location must still be valid")
        self.assertIsInstance(Pyro4.current_context, Pyro4.core._CallContext)

    @unittest.skipIf(sys.version_info >= (3, 7), "async is kw on 3.7+")
    def testAsyncKeywordBackwardsCompatibility(self):
        # 'async' function
        async_function = getattr(Pyro4, "async")
        self.assertIs(async_function, Pyro4.asyncproxy)
        async_function = getattr(Pyro4.core, "async")
        self.assertIs(async_function, Pyro4.core.asyncproxy)
        # 'async' keyword on batch proxy's __call__
        proxy = Pyro4.Proxy("PYRO:dummy@localhost:9999")
        batch = Pyro4.batch(proxy)
        result = batch(**{"async": True})
        result.set_cancelled()
        result = batch(asynchronous=True)
        result.set_cancelled()
        # 'async' keyword on 'proxy._pyroAsync' method
        proxy._pyroAsync(**{"async": True})
        proxy._pyroAsync(asynchronous=True)
        proxy._pyroAsync(True)
        # 'async' keyword on 'async' function
        Pyro4.asyncproxy(proxy, **{"async": True})
        Pyro4.asyncproxy(proxy, asynchronous=True)
        Pyro4.asyncproxy(proxy, True)


if __name__ == "__main__":
    unittest.main()
