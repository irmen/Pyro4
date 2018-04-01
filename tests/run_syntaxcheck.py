"""
Run some syntax checks.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import print_function
import os
import sys


sys.path.insert(0, "../src")
sys.path.insert(1, "PyroTests")


def Pyflakes(path, modules):
    try:
        from pyflakes.scripts.pyflakes import checkPath
    except ImportError:
        print("PYFLAKES not installed. Skipping.")
        return
    warnings = 0
    for m in modules:
        warnings += checkPath(os.path.join(path, m))
    print("%d warnings occurred in pyflakes check" % warnings)


def main(args):
    pyropath = "../src/Pyro4"
    pyromodules = [module for module in os.listdir(pyropath) if module.endswith(".py")]
    checkers = args or ["flakes"]
    if "flakes" in checkers:
        print("-" * 20 + "PYFLAKES")
        Pyflakes(pyropath, pyromodules)


if __name__ == "__main__":
    main(sys.argv[1:])
