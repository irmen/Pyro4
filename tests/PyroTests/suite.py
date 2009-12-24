import unittest
import sys
sys.path.insert(0,"../../src")


# add test modules here
modules=["sockettests", "utiltests", "coretests", "namingtests"]

print >>sys.stderr, "gathering testcases from",modules

suite=unittest.TestSuite()
for module in modules:
	m=__import__(module)
	testcases = unittest.defaultTestLoader.loadTestsFromModule(m)
	suite.addTest(testcases)
	
unittest.TextTestRunner(verbosity=2).run(suite)
