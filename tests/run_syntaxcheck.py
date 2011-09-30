"""
Run some syntax checks.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import os
import sys
sys.path.insert(0,"../src")
sys.path.insert(1,"PyroTests")

def Pyflakes(path, modules):
    try:
        from pyflakes.scripts.pyflakes import checkPath
    except ImportError:
        print("PYFLAKES not installed. Skipping.")
        return
    warnings=0
    for m in modules:
        warnings+=checkPath(os.path.join(path,m))
    print("%d warnings occurred in pyflakes check" % warnings)


def Pylint(path, modules):
    try:
        from pylint import lint
    except ImportError:
        print("PYLINT not installed. Skipping.")
        return
    args=["--rcfile=pylint.rc","--files-output=y"]
    for m in modules:
        m=m[:-3]
        if m and m!="__init__":
            args.append("Pyro4."+m)
    try:
        lint.Run(args)  # this will exit the interpreter... :( 
    finally:
        print("Lint done. Check the output files (pylint_*.txt)")

def main(args):
    pyropath="../src/Pyro4"
    pyromodules=[module for module in os.listdir(pyropath) if module.endswith(".py")]
    checkers=args or ["flakes","lint"]
    if "flakes" in checkers:
        print("-"*20+"PYFLAKES")
        Pyflakes(pyropath, pyromodules)
    if "lint" in checkers:
        print("-"*20+"PYLINT")
        Pylint(pyropath, pyromodules)    # lint always last because it wil exit the interpreter! :(


if __name__=="__main__":
    main(sys.argv[1:])
