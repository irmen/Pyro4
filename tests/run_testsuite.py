"""
Run the complete test suite.
use --tox to make this work from Tox.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import unittest
import sys
import os
import Pyro4
Pyro4.config.reset()

from_tox = "--tox" in sys.argv
xml_report = "--xml" in sys.argv

if from_tox:
    # running from Tox, don't screw with paths otherwise it screws up the virtualenv
    pass
else:
    # running from normal shell invocation
    dirname = os.path.dirname(__file__)
    if dirname:
        print("chdir to " + dirname)
        os.chdir(dirname)
    sys.path.insert(0, "../src")  # add Pyro source directory

sys.path.insert(1, "PyroTests")

if __name__ == "__main__":
    # add test modules here
    modules = [module[:-3] for module in sorted(os.listdir("PyroTests")) if module.endswith(".py") and not module.startswith("__")]

    print("gathering testcases from %s" % modules)

    suite = unittest.TestSuite()
    for module in modules:
        m = __import__("PyroTests." + module)
        m = getattr(m, module)
        testcases = unittest.defaultTestLoader.loadTestsFromModule(m)
        suite.addTest(testcases)

    if xml_report:
        print("\nRUNNING UNIT TESTS (XML reporting)...")
        import xmlrunner
        result = xmlrunner.XMLTestRunner(verbosity=1, output="test-reports").run(suite)
    else:
        print("\nRUNNING UNIT TESTS...")
        result = unittest.TextTestRunner(verbosity=1).run(suite)

    if not result.wasSuccessful():
        sys.exit(10)
