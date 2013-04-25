"""
Miscellaneous utilities.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import sys, zlib, logging
import traceback, linecache
import Pyro4

log=logging.getLogger("Pyro4.util")


def getPyroTraceback(ex_type=None, ex_value=None, ex_tb=None):
    """Returns a list of strings that form the traceback information of a
    Pyro exception. Any remote Pyro exception information is included.
    Traceback information is automatically obtained via ``sys.exc_info()`` if
    you do not supply the objects yourself."""
    def formatRemoteTraceback(remote_tb_lines):
        result=[" +--- This exception occured remotely (Pyro) - Remote traceback:"]
        for line in remote_tb_lines:
            if line.endswith("\n"):
                line=line[:-1]
            lines = line.split("\n")
            for line in lines:
                result.append("\n | ")
                result.append(line)
        result.append("\n +--- End of remote traceback\n")
        return result
    try:
        if ex_type is not None and ex_value is None and ex_tb is None:
            # possible old (3.x) call syntax where caller is only providing exception object
            if type(ex_type) is not type:
                raise TypeError("invalid argument: ex_type should be an exception type, or just supply no arguments at all")
        if ex_type is None and ex_tb is None:
            ex_type, ex_value, ex_tb=sys.exc_info()

        remote_tb=getattr(ex_value, "_pyroTraceback", None)
        local_tb=formatTraceback(ex_type, ex_value, ex_tb, Pyro4.config.DETAILED_TRACEBACK)
        if remote_tb:
            remote_tb=formatRemoteTraceback(remote_tb)
            return local_tb + remote_tb
        else:
            # hmm. no remote tb info, return just the local tb.
            return local_tb
    finally:
        # clean up cycle to traceback, to allow proper GC
        del ex_type, ex_value, ex_tb


def formatTraceback(ex_type=None, ex_value=None, ex_tb=None, detailed=False):
    """Formats an exception traceback. If you ask for detailed formatting,
    the result will contain info on the variables in each stack frame.
    You don't have to provide the exception info objects, if you omit them,
    this function will obtain them itself using ``sys.exc_info()``."""
    if ex_type is not None and ex_value is None and ex_tb is None:
        # possible old (3.x) call syntax where caller is only providing exception object
        if type(ex_type) is not type:
            raise TypeError("invalid argument: ex_type should be an exception type, or just supply no arguments at all")
    if ex_type is None and ex_tb is None:
        ex_type, ex_value, ex_tb=sys.exc_info()
    if detailed and sys.platform!="cli":    # detailed tracebacks don't work in ironpython (most of the local vars are omitted)
        def makeStrValue(value):
            try:
                return repr(value)
            except:
                try:
                    return str(value)
                except:
                    return "<ERROR>"
        try:
            result=["-"*52+"\n"]
            result.append(" EXCEPTION %s: %s\n" % (ex_type,ex_value))
            result.append(" Extended stacktrace follows (most recent call last)\n")
            skipLocals=True  # don't print the locals of the very first stackframe
            while ex_tb:
                frame=ex_tb.tb_frame
                sourceFileName=frame.f_code.co_filename
                if "self" in frame.f_locals:
                    location="%s.%s" % (frame.f_locals["self"].__class__.__name__, frame.f_code.co_name)
                else:
                    location=frame.f_code.co_name
                result.append("-"*52+"\n")
                result.append("File \"%s\", line %d, in %s\n" % (sourceFileName, ex_tb.tb_lineno, location))
                result.append("Source code:\n")
                result.append("    "+linecache.getline(sourceFileName, ex_tb.tb_lineno).strip()+"\n")
                if not skipLocals:
                    names=set()
                    names.update(getattr(frame.f_code,"co_varnames",()))
                    names.update(getattr(frame.f_code,"co_names",()))
                    names.update(getattr(frame.f_code,"co_cellvars",()))
                    names.update(getattr(frame.f_code,"co_freevars",()))
                    result.append("Local values:\n")
                    for name in sorted(names):
                        if name in frame.f_locals:
                            value=frame.f_locals[name]
                            result.append("    %s = %s\n" % (name,makeStrValue(value)))
                            if name=="self":
                                # print the local variables of the class instance
                                for name,value in vars(value).items():
                                    result.append("        self.%s = %s\n" % (name,makeStrValue(value)))
                skipLocals=False
                ex_tb=ex_tb.tb_next
            result.append("-"*52+"\n")
            result.append(" EXCEPTION %s: %s\n" % (ex_type, ex_value))
            result.append("-"*52+"\n")
            return result
        except Exception:
            return ["-"*52+"\nError building extended traceback!!! :\n",
                  "".join(traceback.format_exception(*sys.exc_info())) + '-'*52 + '\n',
                  "Original Exception follows:\n",
                  "".join(traceback.format_exception(ex_type, ex_value, ex_tb))]
    else:
        # default traceback format.
        return traceback.format_exception(ex_type, ex_value, ex_tb)


class SerializerBase(object):
    """Base class for (de)serializer implementations (which must be thread safe)"""
    def serializeData(self, data, compress=False):
        """Serialize the given data object, try to compress if told so.
        Returns a tuple of the serialized data (bytes) and a bool indicating if it is compressed or not."""
        data=self.dumps(data)
        return self.__compressdata(data, compress)

    def deserializeData(self, data, compressed=False):
        """Deserializes the given data (bytes). Set compressed to True to decompress the data first."""
        if compressed:
            data=zlib.decompress(data)
        return self.loads(data)

    def serializeCall(self, obj, method, vargs, kwargs, compress=False):
        """Serialize the given method call parameters, try to compress if told so.
        Returns a tuple of the serialized data and a bool indicating if it is compressed or not."""
        data=self.dumpsCall(obj, method, vargs, kwargs)
        return self.__compressdata(data, compress)

    def deserializeCall(self, data, compressed=False):
        """Deserializes the given call data back to (object, method, vargs, kwargs) tuple.
        Set compressed to True to decompress the data first."""
        if compressed:
            data=zlib.decompress(data)
        return self.loadsCall(data)

    def loads(self, data):
        raise NotImplementedError("implement in subclass")

    def loadsCall(self, data):
        raise NotImplementedError("implement in subclass")

    def dumps(self, data):
        raise NotImplementedError("implement in subclass")

    def dumpsCall(self, obj, method, vargs, kwargs):
        raise NotImplementedError("implement in subclass")

    def __compressdata(self, data, compress):
        if not compress or len(data)<200:
            return data, False  # don't waste time compressing small messages
        compressed=zlib.compress(data)
        if len(compressed)<len(data):
            return compressed, True
        return data, False

    def __eq__(self, other):
        """this equality method is only to support the unit tests of this class"""
        return isinstance(other, SerializerBase) and vars(self)==vars(other)
    def __ne__(self, other):
        return not self.__eq__(other)
    __hash__=object.__hash__


class PickleSerializer(SerializerBase):
    """
    A (de)serializer that wraps the Pickle serialization protocol.
    It can optionally compress the serialized data, and is thread safe.
    """
    def dumpsCall(self, obj, method, vargs, kwargs):
        return pickle.dumps((obj, method, vargs, kwargs), pickle.HIGHEST_PROTOCOL)
    def dumps(self, data):
        return pickle.dumps(data, pickle.HIGHEST_PROTOCOL)
    def loadsCall(self, data):
        return pickle.loads(data)
    def loads(self, data):
        return pickle.loads(data)


class MarshalSerializer(SerializerBase):
    """(de)serializer that wraps the marshal serialization protocol."""
    def dumpsCall(self, obj, method, vargs, kwargs):
        return marshal.dumps((obj, method, vargs, kwargs))
    def dumps(self, data):
        return marshal.dumps(data)
    def loadsCall(self, data):
        return marshal.loads(data)
    def loads(self, data):
        return marshal.loads(data)


class SerpentSerializer(SerializerBase):
    """(de)serializer that wraps the serpent serialization protocol."""
    def dumpsCall(self, obj, method, vargs, kwargs):
        return serpent.dumps((obj, method, vargs, kwargs))
    def dumps(self, data):
        return serpent.dumps(data)
    def loadsCall(self, data):
        return serpent.loads(data)
    def loads(self, data):
        return serpent.loads(data)


class JsonSerializer(SerializerBase):
    """(de)serializer that wraps the json serialization protocol."""
    if sys.version_info<(3,0):
        def dumpsCall(self, object, method, vargs, kwargs):
            data = {"object": object, "method": method, "params": vargs, "kwargs": kwargs}
            return json.dumps(data, ensure_ascii=False)
        def dumps(self, data):
            return json.dumps(data, ensure_ascii=False)
        def loadsCall(self, data):
            data = json.loads(data)
            return data["object"], data["method"], data["params"], data["kwargs"]
        def loads(self, data):
            return json.loads(data)
    else:
        def dumpsCall(self, object, method, vargs, kwargs):
            data = {"object": object, "method": method, "params": vargs, "kwargs": kwargs}
            data = json.dumps(data, ensure_ascii=False)
            return data.encode("utf-8")
        def dumps(self, data):
            data = json.dumps(data, ensure_ascii=False)
            return data.encode("utf-8")
        def loadsCall(self, data):
            data=data.decode("utf-8")
            data = json.loads(data)
            return data["object"], data["method"], data["params"], data["kwargs"]
        def loads(self, data):
            data=data.decode("utf-8")
            return json.loads(data)


class XmlrpcSerializer(SerializerBase):
    """(de)serializer that wraps the xmlrpc serialization protocol."""
    if sys.version_info<(3,0):
        def dumpsCall(self, object, method, vargs, kwargs):
            data = {"object": object, "method": method, "vargs": vargs, "kwargs": kwargs}
            return xmlrpc.dumps((data,), "pyrocall", allow_none=True, encoding="utf-8")
        def dumps(self, data):
            return xmlrpc.dumps((data,), methodresponse=True, allow_none=True, encoding="utf-8")
        def loadsCall(self, data):
            data = xmlrpc.loads(data)[0][0]
            return data["object"], data["method"], data["vargs"], data["kwargs"]
        def loads(self, data):
            return xmlrpc.loads(data)[0][0]
    else:
        def dumpsCall(self, object, method, vargs, kwargs):
            data = {"object": object, "method": method, "vargs": vargs, "kwargs": kwargs}
            data = xmlrpc.dumps((data,), "pyrocall", allow_none=True, encoding="utf-8")
            return data.encode("utf-8")
        def dumps(self, data):
            data = xmlrpc.dumps((data,), methodresponse=True, allow_none=True, encoding="utf-8")
            return data.encode("utf-8")
        def loadsCall(self, data):
            data=data.decode("utf-8")
            data = xmlrpc.loads(data)[0][0]
            return data["object"], data["method"], data["vargs"], data["kwargs"]
        def loads(self, data):
            data=data.decode("utf-8")
            return xmlrpc.loads(data)[0][0]


"""The various serializers that are supported"""
serializers = {}

# determine the serializers that are supported
try:
    import cPickle as pickle
except ImportError:
    import pickle
if pickle.HIGHEST_PROTOCOL<2:
    raise RuntimeError("pickle serializer needs to support protocol 2 or higher")
serializers["pickle"] = PickleSerializer()
import marshal
serializers["marshal"] = MarshalSerializer()
try:
    import json
    serializers["json"] = JsonSerializer()
except ImportError:
    pass
try:
    import xmlrpclib as xmlrpc
    serializers["xmlrpc"] = XmlrpcSerializer()
except ImportError:
    try:
        import xmlrpc.client as xmlrpc
        serializers["xmlrpc"] = XmlrpcSerializer()
    except ImportError:
        pass
try:
    import serpent
    serializers["serpent"] = SerpentSerializer()
except ImportError:
    pass


def resolveDottedAttribute(obj, attr, allowDotted):
    """
    Resolves a dotted attribute name to an object.  Raises
    an AttributeError if any attribute in the chain starts with a '``_``'.
    If the optional allowDotted argument is false, dots are not
    supported and this function operates similar to ``getattr(obj, attr)``.
    """
    if allowDotted:
        attrs = attr.split('.')
        for i in attrs:
            if i.startswith('_'):
                raise AttributeError('attempt to access private attribute "%s"' % i)
            else:
                obj = getattr(obj, i)
        return obj
    else:
        return getattr(obj, attr)


def excepthook(ex_type, ex_value, ex_tb):
    """An exception hook you can use for ``sys.excepthook``, to automatically print remote Pyro tracebacks"""
    traceback="".join(getPyroTraceback(ex_type, ex_value, ex_tb))
    sys.stderr.write(traceback)


def fixIronPythonExceptionForPickle(exceptionObject, addAttributes):
    """function to hack around a bug in IronPython where it doesn't pickle
    exception attributes. We piggyback them into the exception's args."""
    if hasattr(exceptionObject, "args"):
        if addAttributes:
            # piggyback the attributes on the exception args instead.
            exceptionObject.args+=(__IronPythonExceptionArgs(vars(exceptionObject)),)
        else:
            # check if there is a piggybacked object in the args
            # if there is, extract the exception attributes from it.
            if len(exceptionObject.args) > 0:
                piggyback = exceptionObject.args[-1]
                if isinstance(piggyback, __IronPythonExceptionArgs):
                    exceptionObject.args = exceptionObject.args[:-1]
                    exceptionObject.__dict__.update(piggyback.data)


class __IronPythonExceptionArgs(object):
    """Helper class to hold exception arguments for IronPython.
    Separate class otherwise pickling the exception will fail."""
    def __init__(self,data):
        self.data=data
