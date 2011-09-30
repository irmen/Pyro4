"""
Support code for the test suite.
There's some Python 2.x <-> 3.x compatibility code here.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import sys

__all__=["tobytes", "unicode", "unichr", "StringIO","next"]

if sys.version_info<(3,0):
    from StringIO import StringIO
    def tobytes(string, encoding=None):
        return string
    unicode=unicode
    unichr=unichr
else:
    from io import StringIO
    def tobytes(string, encoding="iso-8859-1"):
        return bytes(string,encoding)
    unicode=str
    unichr=chr


if sys.version_info<(2,6):
    def next(iterable):
        return iterable.next()
else:
    next=next
