"""
Run the complete test suite. Doesn't require nose and coverage,
but is more braindead and gives less output.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import unittest
import sys, os

if len(sys.argv)==2 and sys.argv[1]=="--tox":
    # running from Tox, don't screw with paths otherwise it screws up the virtualenv
    pass
else:
    # running from normal shell invocation
    sys.path.insert(0,"../src")    # add Pyro source directory

sys.path.insert(1,"PyroTests")

if __name__=="__main__":
    # add test modules here
    modules=[module[:-3] for module in os.listdir("PyroTests") if module.endswith(".py") and not module.startswith("__")]
     
    print("gathering testcases from %s" % modules)

    suite=unittest.TestSuite()
    for module in modules:
        m=__import__("PyroTests."+module)
        m=getattr(m,module)
        testcases = unittest.defaultTestLoader.loadTestsFromModule(m)
        suite.addTest(testcases)

    print("\nRUNNING UNIT TESTS...")
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        sys.exit(10)

