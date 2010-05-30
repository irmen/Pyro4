import unittest
import os
import servertests

# tests that require a running Pyro server (daemon)
# the server part here is using a timeout setting.


class ServerTestsThreadTimeout(servertests.ServerTestsThreadNoTimeout):
    SERVERTYPE="thread"
    COMMTIMEOUT=2.0
    def testServerParallelism(self):
        # this test is not suitable on a server with timeout set
        pass
    def testProxySharing(self):
        pass
    
if os.name!="java":
    class ServerTestsSelectTimeout(servertests.ServerTestsSelectNoTimeout):
        SERVERTYPE="select"
        COMMTIMEOUT=2.0
        def testServerParallelism(self):
            # this test is not suitable on a server with timeout set
            pass
        def testProxySharing(self):
            pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
