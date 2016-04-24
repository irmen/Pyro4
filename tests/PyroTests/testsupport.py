"""
Support code for the test suite.
There's some Python 2.x <-> 3.x compatibility code here.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import sys
import pickle
import Pyro4

__all__ = ["tobytes", "tostring", "unicode", "unichr", "basestring", "StringIO",
           "NonserializableError", "MyThing", "MyThingExposed", "MyThingExposedSub", "MyThingSub"]

if sys.version_info < (3, 0):
    # noinspection PyUnresolvedReferences
    from StringIO import StringIO

    def tobytes(string, encoding=None):
        return string

    def tostring(bytes):
        return bytes

    unicode = unicode
    unichr = unichr
    basestring = basestring
else:
    from io import StringIO

    def tobytes(string, encoding="iso-8859-1"):
        return bytes(string, encoding)

    def tostring(bytes, encoding="utf-8"):
        return str(bytes, encoding)

    unicode = str
    unichr = chr
    basestring = str


class NonserializableError(Exception):
    def __reduce__(self):
        raise pickle.PicklingError("to make this error non-serializable")


class MyThing(object):
    c_attr = "hi"
    propvalue = 42
    _private_attr1 = "hi"
    __private_attr2 = "hi"
    name = ""

    def __init__(self, name="dummy"):
        self.name = name

    def __eq__(self, other):
        if type(other) is MyThing:
            return self.name == other.name
        return False

    def method(self, arg, default=99, **kwargs):
        pass

    @staticmethod
    def staticmethod(arg):
        pass

    @classmethod
    def classmethod(cls, arg):
        pass

    def __dunder__(self):
        pass

    def __private(self):
        pass

    def _private(self):
        pass

    @Pyro4.expose
    @property
    def prop1(self):
        return self.propvalue

    @Pyro4.expose
    @prop1.setter
    def prop1(self, value):
        self.propvalue = value

    @Pyro4.expose
    @property
    def readonly_prop1(self):
        return self.propvalue

    @property
    def prop2(self):
        return self.propvalue

    @prop2.setter
    def prop2(self, value):
        self.propvalue = value

    @Pyro4.oneway
    def oneway(self, arg):
        pass

    @Pyro4.expose
    def exposed(self):
        pass

    __hash__ = object.__hash__


@Pyro4.expose()
class MyThingExposed(object):
    blurp = 99   # won't be exposed, because it is a class attribute and not a property
    _name = ""

    def __init__(self, name="dummy"):
        self._name = name

    def __eq__(self, other):
        if type(other) is MyThingExposed:
            return self._name == other._name
        return False

    def foo(self, arg):
        return arg

    @classmethod
    def classmethod(cls, arg):
        return arg

    @staticmethod
    def staticmethod(arg):
        return arg

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def readonly_name(self):
        return self._name

    @Pyro4.oneway
    def remotemethod(self, arg):
        return arg

    def _p(self):
        pass

    def __private(self):
        pass

    def __dunder__(self):
        pass

    __hash__ = object.__hash__


class MyThingExposedSub(MyThingExposed):
    def sub_exposed(self):
        pass

    def sub_unexposed(self):
        pass


class MyThingSub(MyThing):
    @Pyro4.expose
    def sub_exposed(self):
        pass

    def sub_unexposed(self):
        pass
