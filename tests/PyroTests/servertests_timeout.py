import unittest
import os
import servertests

# tests that require a running Pyro server (daemon)
# the server part here is using a timeout setting.


class ServerTestsThreadTimeout(servertests.ServerTestsThreadNoTimeout):
    SERVERTYPE="thread"
    COMMTIMEOUT=2

if os.name!="java":
    class ServerTestsSelectTimeout(servertests.ServerTestsSelectNoTimeout):
        SERVERTYPE="select"
        COMMTIMEOUT=2


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
