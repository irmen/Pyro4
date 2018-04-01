"""
Support code for the test suite.
There's some Python 2.x <-> 3.x compatibility code here.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import sys
import pickle
import threading
from Pyro4 import errors, core, expose, behavior, current_context
from Pyro4.configuration import config


__all__ = ["tobytes", "tostring", "unicode", "unichr", "basestring", "StringIO",
           "NonserializableError", "MyThingPartlyExposed", "MyThingFullExposed",
           "MyThingExposedSub", "MyThingPartlyExposedSub", "ConnectionMock",
           "AtomicCounter", "ResourceService", "Resource"]


config.reset(False)   # reset the config to default

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


class MyThingPartlyExposed(object):
    c_attr = "hi"
    propvalue = 42
    _private_attr1 = "hi"
    __private_attr2 = "hi"
    name = ""

    def __init__(self, name="dummy"):
        self.name = name

    def __eq__(self, other):
        if type(other) is MyThingPartlyExposed:
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

    @core.expose
    @property
    def prop1(self):
        return self.propvalue

    @core.expose
    @prop1.setter
    def prop1(self, value):
        self.propvalue = value

    @core.expose
    @property
    def readonly_prop1(self):
        return self.propvalue

    @property
    def prop2(self):
        return self.propvalue

    @prop2.setter
    def prop2(self, value):
        self.propvalue = value

    @core.oneway
    @core.expose
    def oneway(self, arg):
        pass

    @core.expose
    def exposed(self):
        pass

    __hash__ = object.__hash__


@core.expose
class MyThingFullExposed(object):
    """this is the same as MyThingPartlyExposed but the whole class should be exposed"""
    c_attr = "hi"
    propvalue = 42
    _private_attr1 = "hi"
    __private_attr2 = "hi"
    name = ""

    def __init__(self, name="dummy"):
        self.name = name    # note: not affected by @expose, only real properties are

    def __eq__(self, other):
        if type(other) is MyThingFullExposed:
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

    @property
    def prop1(self):
        return self.propvalue

    @prop1.setter
    def prop1(self, value):
        self.propvalue = value

    @property
    def readonly_prop1(self):
        return self.propvalue

    @property
    def prop2(self):
        return self.propvalue

    @prop2.setter
    def prop2(self, value):
        self.propvalue = value

    @core.oneway
    def oneway(self, arg):
        pass

    def exposed(self):
        pass

    __hash__ = object.__hash__


@core.expose
class MyThingExposedSub(MyThingFullExposed):
    def sub_exposed(self):
        pass

    def sub_unexposed(self):
        pass

    @core.oneway
    def oneway2(self):
        pass


class MyThingPartlyExposedSub(MyThingPartlyExposed):
    @core.expose
    def sub_exposed(self):
        pass

    def sub_unexposed(self):
        pass

    @core.oneway
    def oneway2(self):
        pass


class ConnectionMock(object):
    def __init__(self, initial_msg=None):
        self.keep_open = False
        if not initial_msg:
            self.received = b""
        elif isinstance(initial_msg, (str, bytes)):
            self.received = initial_msg
        else:
            self.received = initial_msg.to_bytes()   # it's probably a Message object

    def send(self, data):
        self.received += data

    def recv(self, datasize):
        chunk = self.received[:datasize]
        self.received = self.received[datasize:]
        if len(chunk) < datasize:
            raise errors.ConnectionClosedError("receiving: not enough data")
        return chunk


class AtomicCounter(object):
    def __init__(self, value=0):
        self.__initial = value
        self.__value = value
        self.__lock = threading.Lock()

    def reset(self):
        self.__value = self.__initial

    def incr(self, amount=1):
        with self.__lock:
            self.__value += amount
            return self.__value

    def decr(self, amount=1):
        with self.__lock:
            self.__value -= amount
            return self.__value

    @property
    def value(self):
        return self.__value


class Resource(object):
    # a fictional resource that gets allocated and must be freed again later.
    def __init__(self, name, collection):
        self.name = name
        self.collection = collection
        self.close_called = False

    def close(self):
        # Pyro will call this on a tracked resource once the client's connection gets closed!
        self.collection.discard(self)
        self.close_called = True


@expose
@behavior(instance_mode="single")
class ResourceService(object):
    def __init__(self):
        self.resources = set()      # the allocated resources

    def allocate(self, name):
        resource = Resource(name, self.resources)
        self.resources.add(resource)
        current_context.track_resource(resource)

    def free(self, name):
        resources = {r for r in self.resources if r.name == name}
        self.resources -= resources
        for r in resources:
            r.close()
            current_context.untrack_resource(r)

    def list(self):
        return [r.name for r in self.resources]
