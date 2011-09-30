"""
Run the complete test suite.

This requires nose and coverage to be installed.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import sys
import nose

sys.path.insert(0,"../src")    # add Pyro source directory

nose.main(argv=["noserunner", "--cover-erase","--with-coverage","--cover-package=Pyro4", "--with-xunit"])

