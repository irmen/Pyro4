"""
Tests for a running Pyro server, with timeouts.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import unittest
import test_server


class ServerTestsThreadTimeout(test_server.ServerTestsThreadNoTimeout):
    SERVERTYPE = "thread"
    COMMTIMEOUT = 2.0

    def testServerParallelism(self):
        # this test is not suitable on a server with timeout set
        pass

    def testProxySharing(self):
        pass

    def testException(self):
        pass


class ServerTestsMultiplexTimeout(test_server.ServerTestsMultiplexNoTimeout):
    SERVERTYPE = "multiplex"
    COMMTIMEOUT = 2.0

    def testServerParallelism(self):
        # this test is not suitable on a server with timeout set
        pass

    def testProxySharing(self):
        pass

    def testException(self):
        pass


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
