"""
Miscellaneous utilities.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import sys, zlib, logging
import traceback, linecache
try:
    import copyreg
except ImportError:
    import copy_reg as copyreg
import Pyro4
import Pyro4.errors
import Pyro4.message

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
                line = line[:-1]
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
            result.append(" EXCEPTION %s: %s\n" % (ex_type, ex_value))
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
                    names.update(getattr(frame.f_code, "co_varnames", ()))
                    names.update(getattr(frame.f_code, "co_names", ()))
                    names.update(getattr(frame.f_code, "co_cellvars", ()))
                    names.update(getattr(frame.f_code, "co_freevars", ()))
                    result.append("Local values:\n")
                    for name in sorted(names):
                        if name in frame.f_locals:
                            value=frame.f_locals[name]
                            result.append("    %s = %s\n" % (name, makeStrValue(value)))
                            if name=="self":
                                # print the local variables of the class instance
                                for name, value in vars(value).items():
                                    result.append("        self.%s = %s\n" % (name, makeStrValue(value)))
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


all_exceptions = {}
if sys.version_info < (3, 0):
    import exceptions
    for name, t in vars(exceptions).items():
        if type(t) is type and issubclass(t, BaseException):
            all_exceptions[name] = t
else:
    import builtins
    for name, t in vars(builtins).items():
        if type(t) is type and issubclass(t, BaseException):
            all_exceptions[name] = t
for name, t in vars(Pyro4.errors).items():
    if type(t) is type and issubclass(t, Pyro4.errors.PyroError):
        all_exceptions[name] = t


class SerializerBase(object):
    """Base class for (de)serializer implementations (which must be thread safe)"""
    __custom_class_to_dict_registry = {}

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

    @classmethod
    def register_type_replacement(cls, object_type, replacement_function):
        raise NotImplementedError("implement in subclass")

    @classmethod
    def register_class_to_dict(cls, clazz, converter):
        cls.__custom_class_to_dict_registry[clazz] = converter

    @classmethod
    def unregister_class_to_dict(cls, clazz):
        if clazz in cls.__custom_class_to_dict_registry:
            del cls.__custom_class_to_dict_registry[clazz]

    @classmethod
    def class_to_dict(cls, obj):
        """Convert a non-serializable object to a dict. Mostly borrowed from serpent."""
        for clazz in cls.__custom_class_to_dict_registry:
            if isinstance(obj, clazz):
                return cls.__custom_class_to_dict_registry[clazz](obj)
        if type(obj) in (set, dict, tuple, list):
            raise Pyro4.errors.ProtocolError("couldn't serialize sequence " + str(obj.__class__) + ", one of its elements is unserializable")
        if hasattr(obj, "_pyroDaemon"):
            obj._pyroDaemon = None
        if isinstance(obj, BaseException):
            # special case for exceptions
            value={"args": obj.args}
            value["__class__"] = obj.__class__.__module__ + "." + obj.__class__.__name__
            value["attributes"] = vars(obj)  # add custom exception attributes
            return value
        try:
            value = obj.__getstate__()
        except AttributeError:
            pass
        else:
            if isinstance(value, dict):
                return value
        try:
            value = dict(vars(obj))  # make sure we can serialize anything that resembles a dict
            value["__class__"] = obj.__class__.__module__ + "." + obj.__class__.__name__
            return value
        except TypeError:
            if hasattr(obj, "__slots__"):
                # use the __slots__ instead of the vars dict
                value = {}
                for slot in obj.__slots__:
                    value[slot] = getattr(obj, slot)
                value["__class__"] = obj.__class__.__module__ + "." + obj.__class__.__name__
                return value
            else:
                raise Pyro4.errors.ProtocolError("don't know how to serialize class " + str(obj.__class__) + ". Give it vars() or an appropriate __getstate__")

    @staticmethod
    def dict_to_class(data):
        """
        Recreate an object out of a dict containing the class name and the attributes.
        Only a fixed set of classes are recognized.
        """
        classname = data.get("__class__", "<unknown>")
        if "__" in classname:
            raise Pyro4.errors.SecurityError("refused to deserialize types with double underscores in their name: "+classname)
        if classname.startswith("Pyro4.core."):
            if classname=="Pyro4.core.URI":
                uri = Pyro4.core.URI.__new__(Pyro4.core.URI)
                uri.__setstate__(data["state"])
                return uri
            elif classname=="Pyro4.core.Proxy":
                proxy = Pyro4.core.Proxy.__new__(Pyro4.core.Proxy)
                state = data["state"]
                uri = Pyro4.core.URI(state[0])
                oneway = set(state[1])
                timeout = state[2]
                proxy.__setstate__((uri, oneway, timeout))
                return proxy
            elif classname=="Pyro4.core.Daemon":
                return Pyro4.core.Daemon.__new__(Pyro4.core.Daemon)
        elif classname.startswith("Pyro4.util."):
            if classname=="Pyro4.util.PickleSerializer":
                return PickleSerializer()
            elif classname=="Pyro4.util.MarshalSerializer":
                return MarshalSerializer()
            elif classname=="Pyro4.util.JsonSerializer":
                return JsonSerializer()
            elif classname=="Pyro4.util.SerpentSerializer":
                return SerpentSerializer()
        elif classname.startswith("Pyro4.errors."):
            errortype = getattr(Pyro4.errors, classname.split('.', 2)[2])
            if issubclass(errortype, Pyro4.errors.PyroError):
                return SerializerBase.make_exception(errortype, data)
        elif classname == "Pyro4.futures._ExceptionWrapper":
            ex = SerializerBase.dict_to_class(data["exception"])
            return Pyro4.futures._ExceptionWrapper(ex)
        elif classname.startswith("builtins."):
            exceptiontype = getattr(builtins, classname.split('.', 1)[1])
            if issubclass(exceptiontype, BaseException):
                return SerializerBase.make_exception(exceptiontype, data)
        elif classname.startswith("exceptions."):
            exceptiontype = getattr(exceptions, classname.split('.', 1)[1])
            if issubclass(exceptiontype, BaseException):
                return SerializerBase.make_exception(exceptiontype, data)
        elif classname in all_exceptions:
            return SerializerBase.make_exception(all_exceptions[classname], data)
        # try one of the serializer classes
        for serializer in _serializers.values():
            if classname == serializer.__class__.__name__:
                return serializer
        raise Pyro4.errors.ProtocolError("unsupported serialized class: "+classname)

    @staticmethod
    def make_exception(exceptiontype, data):
        ex = exceptiontype(*data["args"])
        if "attributes" in data:
            # restore custom attributes on the exception object
            for attr, value in data["attributes"].items():
                setattr(ex, attr, value)
        return ex

    def recreate_classes(self, literal):
        t = type(literal)
        if t is set:
            return set([self.recreate_classes(x) for x in literal])
        if t is list:
            return [self.recreate_classes(x) for x in literal]
        if t is tuple:
            return tuple(self.recreate_classes(x) for x in literal)
        if t is dict:
            if "__class__" in literal:
                return self.dict_to_class(literal)
            result = {}
            for key, value in literal.items():
                result[key] = self.recreate_classes(value)
            return result
        return literal

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
    serializer_id = Pyro4.message.SERIALIZER_PICKLE

    def dumpsCall(self, obj, method, vargs, kwargs):
        return pickle.dumps((obj, method, vargs, kwargs), pickle.HIGHEST_PROTOCOL)

    def dumps(self, data):
        return pickle.dumps(data, pickle.HIGHEST_PROTOCOL)

    def loadsCall(self, data):
        return pickle.loads(data)

    def loads(self, data):
        return pickle.loads(data)

    @classmethod
    def register_type_replacement(cls, object_type, replacement_function):
        def copyreg_function(obj):
            return replacement_function(obj).__reduce__()
        try:
            copyreg.pickle(object_type, copyreg_function)
        except TypeError:
            pass


class MarshalSerializer(SerializerBase):
    """(de)serializer that wraps the marshal serialization protocol."""
    serializer_id = Pyro4.message.SERIALIZER_MARSHAL

    def dumpsCall(self, obj, method, vargs, kwargs):
        return marshal.dumps((obj, method, vargs, kwargs))

    def dumps(self, data):
        try:
            return marshal.dumps(data)
        except (ValueError, TypeError):
            return marshal.dumps(self.class_to_dict(data))

    def loadsCall(self, data):
        obj, method, vargs, kwargs = marshal.loads(data)
        vargs = self.recreate_classes(vargs)
        kwargs = self.recreate_classes(kwargs)
        return obj, method, vargs, kwargs

    def loads(self, data):
        return self.recreate_classes(marshal.loads(data))

    @classmethod
    def register_type_replacement(cls, object_type, replacement_function):
        pass    # marshal serializer doesn't support per-type hooks


class SerpentSerializer(SerializerBase):
    """(de)serializer that wraps the serpent serialization protocol."""
    serializer_id = Pyro4.message.SERIALIZER_SERPENT

    def dumpsCall(self, obj, method, vargs, kwargs):
        return serpent.dumps((obj, method, vargs, kwargs))

    def dumps(self, data):
        return serpent.dumps(data)

    def loadsCall(self, data):
        obj, method, vargs, kwargs = serpent.loads(data)
        vargs = self.recreate_classes(vargs)
        kwargs = self.recreate_classes(kwargs)
        return obj, method, vargs, kwargs

    def loads(self, data):
        return self.recreate_classes(serpent.loads(data))

    @classmethod
    def register_type_replacement(cls, object_type, replacement_function):
        def custom_serializer(object, serpent_serializer, outputstream, indentlevel):
            replaced = replacement_function(object)
            if replaced is object:
                serpent_serializer.ser_default_class(replaced, outputstream, indentlevel)
            else:
                serpent_serializer._serialize(replaced, outputstream, indentlevel)
        serpent.register_class(object_type, custom_serializer)


class JsonSerializer(SerializerBase):
    """(de)serializer that wraps the json serialization protocol."""
    serializer_id = Pyro4.message.SERIALIZER_JSON

    __type_replacements = {}
    def dumpsCall(self, obj, method, vargs, kwargs):
        data = {"object": obj, "method": method, "params": vargs, "kwargs": kwargs}
        data = json.dumps(data, ensure_ascii=False, default=self.default)
        return data.encode("utf-8")
    def dumps(self, data):
        data = json.dumps(data, ensure_ascii=False, default=self.default)
        return data.encode("utf-8")
    def loadsCall(self, data):
        data=data.decode("utf-8")
        data = json.loads(data)
        vargs = self.recreate_classes(data["params"])
        kwargs = self.recreate_classes(data["kwargs"])
        return data["object"], data["method"], vargs, kwargs
    def loads(self, data):
        data=data.decode("utf-8")
        return self.recreate_classes(json.loads(data))
    def default(self, obj):
        replacer = self.__type_replacements.get(type(obj), None)
        if replacer:
            obj = replacer(obj)
        return self.class_to_dict(obj)
    @classmethod
    def register_type_replacement(cls, object_type, replacement_function):
        cls.__type_replacements[object_type] = replacement_function


"""The various serializers that are supported"""
_serializers = {}
_serializers_by_id = {}
def get_serializer(name):
    try:
        return _serializers[name]
    except KeyError:
        raise Pyro4.errors.ProtocolError("serializer '%s' is unknown or not available" % name)

def get_serializer_by_id(sid):
    try:
        return _serializers_by_id[sid]
    except KeyError:
        raise Pyro4.errors.ProtocolError("no serializer available for id %d" % sid)

# determine the serializers that are supported
try:
    import cPickle as pickle
except ImportError:
    import pickle
assert pickle.HIGHEST_PROTOCOL>=2, "pickle needs to support protocol 2 or higher"
_ser = PickleSerializer()
_serializers["pickle"] = _ser
_serializers_by_id[_ser.serializer_id] = _ser
import marshal
_ser = MarshalSerializer()
_serializers["marshal"] = _ser
_serializers_by_id[_ser.serializer_id] = _ser
try:
    import json
    _ser = JsonSerializer()
    _serializers["json"] = _ser
    _serializers_by_id[_ser.serializer_id] = _ser
except ImportError:
    pass
try:
    import serpent
    if '-' in serpent.__version__:
        ver = serpent.__version__.split('-', 1)[0]
    else:
        ver = serpent.__version__
    ver = tuple(map(int, ver.split(".")))
    if ver<(1,3):
        raise RuntimeError("requires serpent 1.3 or better")
    _ser = SerpentSerializer()
    _serializers["serpent"] = _ser
    _serializers_by_id[_ser.serializer_id] = _ser
except ImportError:
    #warnings.warn("serpent serializer not available", RuntimeWarning)
    pass
del _ser


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
    traceback = "".join(getPyroTraceback(ex_type, ex_value, ex_tb))
    sys.stderr.write(traceback)


def fixIronPythonExceptionForPickle(exceptionObject, addAttributes):
    """
    Function to hack around a bug in IronPython where it doesn't pickle
    exception attributes. We piggyback them into the exception's args.
    Bug report is at http://ironpython.codeplex.com/workitem/30805
    """
    if hasattr(exceptionObject, "args"):
        if addAttributes:
            # piggyback the attributes on the exception args instead.
            ironpythonArgs = vars(exceptionObject)
            ironpythonArgs["__ironpythonargs__"] = True
            exceptionObject.args += (ironpythonArgs,)
        else:
            # check if there is a piggybacked object in the args
            # if there is, extract the exception attributes from it.
            if len(exceptionObject.args) > 0:
                piggyback = exceptionObject.args[-1]
                if type(piggyback) is dict and piggyback.get("__ironpythonargs__"):
                    del piggyback["__ironpythonargs__"]
                    exceptionObject.args = exceptionObject.args[:-1]
                    exceptionObject.__dict__.update(piggyback)
