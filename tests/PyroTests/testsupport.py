"""
Support code for the test suite.
There's some Python 2.x <-> 3.x compatibility code here.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import sys
import threading

__all__=["tobytes", "unicode", "unichr", "StringIO", "next", "AtomicCounter"]

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


class AtomicCounter(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.count = 0
    def reset(self):
        self.count = 0
    def incr(self):
        with self.lock:
            self.count += 1
    def value(self):
        with self.lock:
            return self.count

