"""
Miscellaneous utilities, and serializers.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import array
import sys
import zlib
import uuid
import logging
import linecache
import traceback
import inspect
import struct
import datetime
import decimal
import numbers
from Pyro4 import errors
from Pyro4.configuration import config

try:
    import copyreg
except ImportError:
    import copy_reg as copyreg

log = logging.getLogger("Pyro4.util")


def getPyroTraceback(ex_type=None, ex_value=None, ex_tb=None):
    """Returns a list of strings that form the traceback information of a
    Pyro exception. Any remote Pyro exception information is included.
    Traceback information is automatically obtained via ``sys.exc_info()`` if
    you do not supply the objects yourself."""

    def formatRemoteTraceback(remote_tb_lines):
        result = [" +--- This exception occured remotely (Pyro) - Remote traceback:"]
        for line in remote_tb_lines:
            if line.endswith("\n"):
                line = line[:-1]
            lines = line.split("\n")
            for line2 in lines:
                result.append("\n | ")
                result.append(line2)
        result.append("\n +--- End of remote traceback\n")
        return result

    try:
        if ex_type is not None and ex_value is None and ex_tb is None:
            # possible old (3.x) call syntax where caller is only providing exception object
            if type(ex_type) is not type:
                raise TypeError("invalid argument: ex_type should be an exception type, or just supply no arguments at all")
        if ex_type is None and ex_tb is None:
            ex_type, ex_value, ex_tb = sys.exc_info()

        remote_tb = getattr(ex_value, "_pyroTraceback", None)
        local_tb = formatTraceback(ex_type, ex_value, ex_tb, config.DETAILED_TRACEBACK)
        if remote_tb:
            remote_tb = formatRemoteTraceback(remote_tb)
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
        ex_type, ex_value, ex_tb = sys.exc_info()
    if detailed and sys.platform != "cli":  # detailed tracebacks don't work in ironpython (most of the local vars are omitted)
        def makeStrValue(value):
            try:
                return repr(value)
            except:
                try:
                    return str(value)
                except:
                    return "<ERROR>"

        try:
            result = ["-" * 52 + "\n"]
            result.append(" EXCEPTION %s: %s\n" % (ex_type, ex_value))
            result.append(" Extended stacktrace follows (most recent call last)\n")
            skipLocals = True  # don't print the locals of the very first stack frame
            while ex_tb:
                frame = ex_tb.tb_frame
                sourceFileName = frame.f_code.co_filename
                if "self" in frame.f_locals:
                    location = "%s.%s" % (frame.f_locals["self"].__class__.__name__, frame.f_code.co_name)
                else:
                    location = frame.f_code.co_name
                result.append("-" * 52 + "\n")
                result.append("File \"%s\", line %d, in %s\n" % (sourceFileName, ex_tb.tb_lineno, location))
                result.append("Source code:\n")
                result.append("    " + linecache.getline(sourceFileName, ex_tb.tb_lineno).strip() + "\n")
                if not skipLocals:
                    names = set()
                    names.update(getattr(frame.f_code, "co_varnames", ()))
                    names.update(getattr(frame.f_code, "co_names", ()))
                    names.update(getattr(frame.f_code, "co_cellvars", ()))
                    names.update(getattr(frame.f_code, "co_freevars", ()))
                    result.append("Local values:\n")
                    for name2 in sorted(names):
                        if name2 in frame.f_locals:
                            value = frame.f_locals[name2]
                            result.append("    %s = %s\n" % (name2, makeStrValue(value)))
                            if name2 == "self":
                                # print the local variables of the class instance
                                for name3, value in vars(value).items():
                                    result.append("        self.%s = %s\n" % (name3, makeStrValue(value)))
                skipLocals = False
                ex_tb = ex_tb.tb_next
            result.append("-" * 52 + "\n")
            result.append(" EXCEPTION %s: %s\n" % (ex_type, ex_value))
            result.append("-" * 52 + "\n")
            return result
        except Exception:
            return ["-" * 52 + "\nError building extended traceback!!! :\n",
                    "".join(traceback.format_exception(*sys.exc_info())) + '-' * 52 + '\n',
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
    buffer = bytearray
for name, t in vars(errors).items():
    if type(t) is type and issubclass(t, errors.PyroError):
        all_exceptions[name] = t


class SerializerBase(object):
    """Base class for (de)serializer implementations (which must be thread safe)"""
    __custom_class_to_dict_registry = {}
    __custom_dict_to_class_registry = {}

    def serializeData(self, data, compress=False):
        """Serialize the given data object, try to compress if told so.
        Returns a tuple of the serialized data (bytes) and a bool indicating if it is compressed or not."""
        data = self.dumps(data)
        return self.__compressdata(data, compress)

    def deserializeData(self, data, compressed=False):
        """Deserializes the given data (bytes). Set compressed to True to decompress the data first."""
        if compressed:
            if sys.version_info < (3, 0):
                data = self._convertToBytes(data)
            data = zlib.decompress(data)
        return self.loads(data)

    def serializeCall(self, obj, method, vargs, kwargs, compress=False):
        """Serialize the given method call parameters, try to compress if told so.
        Returns a tuple of the serialized data and a bool indicating if it is compressed or not."""
        data = self.dumpsCall(obj, method, vargs, kwargs)
        return self.__compressdata(data, compress)

    def deserializeCall(self, data, compressed=False):
        """Deserializes the given call data back to (object, method, vargs, kwargs) tuple.
        Set compressed to True to decompress the data first."""
        if compressed:
            if sys.version_info < (3, 0):
                data = self._convertToBytes(data)
            data = zlib.decompress(data)
        return self.loadsCall(data)

    def loads(self, data):
        raise NotImplementedError("implement in subclass")

    def loadsCall(self, data):
        raise NotImplementedError("implement in subclass")

    def dumps(self, data):
        raise NotImplementedError("implement in subclass")

    def dumpsCall(self, obj, method, vargs, kwargs):
        raise NotImplementedError("implement in subclass")

    def _convertToBytes(self, data):
        t = type(data)
        if t is not bytes:
            if t in (bytearray, buffer):
                return bytes(data)
            if t is memoryview:
                return data.tobytes()
        return data

    def __compressdata(self, data, compress):
        if not compress or len(data) < 200:
            return data, False  # don't waste time compressing small messages
        compressed = zlib.compress(data)
        if len(compressed) < len(data):
            return compressed, True
        return data, False

    @classmethod
    def register_type_replacement(cls, object_type, replacement_function):
        raise NotImplementedError("implement in subclass")

    @classmethod
    def register_class_to_dict(cls, clazz, converter, serpent_too=True):
        """Registers a custom function that returns a dict representation of objects of the given class.
        The function is called with a single parameter; the object to be converted to a dict."""
        cls.__custom_class_to_dict_registry[clazz] = converter
        if serpent_too:
            try:
                get_serializer_by_id(SerpentSerializer.serializer_id)
                import serpent      # @todo not needed?

                def serpent_converter(obj, serializer, stream, level):
                    d = converter(obj)
                    serializer.ser_builtins_dict(d, stream, level)

                serpent.register_class(clazz, serpent_converter)
            except errors.ProtocolError:
                pass

    @classmethod
    def unregister_class_to_dict(cls, clazz):
        """Removes the to-dict conversion function registered for the given class. Objects of the class
        will be serialized by the default mechanism again."""
        if clazz in cls.__custom_class_to_dict_registry:
            del cls.__custom_class_to_dict_registry[clazz]
        try:
            get_serializer_by_id(SerpentSerializer.serializer_id)
            import serpent          # @todo not needed?
            serpent.unregister_class(clazz)
        except errors.ProtocolError:
            pass

    @classmethod
    def register_dict_to_class(cls, classname, converter):
        """
        Registers a custom converter function that creates objects from a dict with the given classname tag in it.
        The function is called with two parameters: the classname and the dictionary to convert to an instance of the class.

        This mechanism is not used for the pickle serializer.
        """
        cls.__custom_dict_to_class_registry[classname] = converter

    @classmethod
    def unregister_dict_to_class(cls, classname):
        """
        Removes the converter registered for the given classname. Dicts with that classname tag
        will be deserialized by the default mechanism again.

        This mechanism is not used for the pickle serializer.
        """
        if classname in cls.__custom_dict_to_class_registry:
            del cls.__custom_dict_to_class_registry[classname]

    @classmethod
    def class_to_dict(cls, obj):
        """
        Convert a non-serializable object to a dict. Partly borrowed from serpent.
        Not used for the pickle serializer.
        """
        for clazz in cls.__custom_class_to_dict_registry:
            if isinstance(obj, clazz):
                return cls.__custom_class_to_dict_registry[clazz](obj)
        if type(obj) in (set, dict, tuple, list):
            # we use a ValueError to mirror the exception type returned by serpent and other serializers
            raise ValueError("can't serialize type " + str(obj.__class__) + " into a dict")
        if hasattr(obj, "_pyroDaemon"):
            obj._pyroDaemon = None
        if isinstance(obj, BaseException):
            # special case for exceptions
            return {
                "__class__": obj.__class__.__module__ + "." + obj.__class__.__name__,
                "__exception__": True,
                "args": obj.args,
                "attributes": vars(obj)  # add custom exception attributes
            }
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
                raise errors.SerializeError("don't know how to serialize class " + str(obj.__class__) +
                                            " using serializer " + str(cls.__name__) +
                                            ". Give it vars() or an appropriate __getstate__")

    @classmethod
    def dict_to_class(cls, data):
        """
        Recreate an object out of a dict containing the class name and the attributes.
        Only a fixed set of classes are recognized.
        Not used for the pickle serializer.
        """
        from Pyro4 import core, futures  # XXX circular
        classname = data.get("__class__", "<unknown>")
        if isinstance(classname, bytes):
            classname = classname.decode("utf-8")
        if classname in cls.__custom_dict_to_class_registry:
            converter = cls.__custom_dict_to_class_registry[classname]
            return converter(classname, data)
        if "__" in classname:
            raise errors.SecurityError("refused to deserialize types with double underscores in their name: " + classname)
        # for performance, the constructors below are hardcoded here instead of added on a per-class basis to the dict-to-class registry
        if classname.startswith("Pyro4.core."):
            if classname == "Pyro4.core.URI":
                uri = core.URI.__new__(core.URI)
                uri.__setstate_from_dict__(data["state"])
                return uri
            elif classname == "Pyro4.core.Proxy":
                proxy = core.Proxy.__new__(core.Proxy)
                proxy.__setstate_from_dict__(data["state"])
                return proxy
            elif classname == "Pyro4.core.Daemon":
                daemon = core.Daemon.__new__(core.Daemon)
                daemon.__setstate_from_dict__(data["state"])
                return daemon
        elif classname.startswith("Pyro4.util."):
            if classname == "Pyro4.util.SerpentSerializer":
                return SerpentSerializer()
            elif classname == "Pyro4.util.PickleSerializer":
                return PickleSerializer()
            elif classname == "Pyro4.util.MarshalSerializer":
                return MarshalSerializer()
            elif classname == "Pyro4.util.JsonSerializer":
                return JsonSerializer()
            elif classname == "Pyro4.util.MsgpackSerializer":
                return MsgpackSerializer()
            elif classname == "Pyro4.util.CloudpickleSerializer":
                return CloudpickleSerializer()
            elif classname == "Pyro4.util.DillSerializer":
                return DillSerializer()
        elif classname.startswith("Pyro4.errors."):
            errortype = getattr(errors, classname.split('.', 2)[2])
            if issubclass(errortype, errors.PyroError):
                return SerializerBase.make_exception(errortype, data)
        elif classname == "Pyro4.futures._ExceptionWrapper":
            ex = data["exception"]
            if isinstance(ex, dict) and "__class__" in ex:
                ex = SerializerBase.dict_to_class(ex)
            return futures._ExceptionWrapper(ex)
        elif data.get("__exception__", False):
            if classname in all_exceptions:
                return SerializerBase.make_exception(all_exceptions[classname], data)
            # python 2.x: exceptions.ValueError
            # python 3.x: builtins.ValueError
            # translate to the appropriate namespace...
            namespace, short_classname = classname.split('.', 1)
            if namespace in ("builtins", "exceptions"):
                if sys.version_info < (3, 0):
                    exceptiontype = getattr(exceptions, short_classname)
                    if issubclass(exceptiontype, BaseException):
                        return SerializerBase.make_exception(exceptiontype, data)
                else:
                    exceptiontype = getattr(builtins, short_classname)
                    if issubclass(exceptiontype, BaseException):
                        return SerializerBase.make_exception(exceptiontype, data)
            elif namespace == "sqlite3" and short_classname.endswith("Error"):
                import sqlite3
                exceptiontype = getattr(sqlite3, short_classname)
                if issubclass(exceptiontype, BaseException):
                    return SerializerBase.make_exception(exceptiontype, data)
        log.warning("unsupported serialized class: " + classname)
        raise errors.SerializeError("unsupported serialized class: " + classname)

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
            return {self.recreate_classes(x) for x in literal}
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
        return isinstance(other, SerializerBase) and vars(self) == vars(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    __hash__ = object.__hash__


class PickleSerializer(SerializerBase):
    """
    A (de)serializer that wraps the Pickle serialization protocol.
    It can optionally compress the serialized data, and is thread safe.
    """
    serializer_id = 4  # never change this

    def dumpsCall(self, obj, method, vargs, kwargs):
        return pickle.dumps((obj, method, vargs, kwargs), config.PICKLE_PROTOCOL_VERSION)

    def dumps(self, data):
        return pickle.dumps(data, config.PICKLE_PROTOCOL_VERSION)

    def loadsCall(self, data):
        data = self._convertToBytes(data)
        return pickle.loads(data)

    def loads(self, data):
        data = self._convertToBytes(data)
        return pickle.loads(data)

    @classmethod
    def register_type_replacement(cls, object_type, replacement_function):
        def copyreg_function(obj):
            return replacement_function(obj).__reduce__()

        if object_type is type or not inspect.isclass(object_type):
            raise ValueError("refusing to register replacement for a non-type or the type 'type' itself")
        try:
            copyreg.pickle(object_type, copyreg_function)
        except TypeError:
            pass


class CloudpickleSerializer(SerializerBase):
    """
    A (de)serializer that wraps the Cloudpickle serialization protocol.
    It can optionally compress the serialized data, and is thread safe.
    """
    serializer_id = 7  # never change this

    def dumpsCall(self, obj, method, vargs, kwargs):
        return cloudpickle.dumps((obj, method, vargs, kwargs), config.PICKLE_PROTOCOL_VERSION)

    def dumps(self, data):
        return cloudpickle.dumps(data, config.PICKLE_PROTOCOL_VERSION)

    def loadsCall(self, data):
        return cloudpickle.loads(data)

    def loads(self, data):
        return cloudpickle.loads(data)

    @classmethod
    def register_type_replacement(cls, object_type, replacement_function):
        def copyreg_function(obj):
            return replacement_function(obj).__reduce__()

        if object_type is type or not inspect.isclass(object_type):
            raise ValueError("refusing to register replacement for a non-type or the type 'type' itself")
        try:
            copyreg.pickle(object_type, copyreg_function)
        except TypeError:
            pass


class DillSerializer(SerializerBase):
    """
    A (de)serializer that wraps the Dill serialization protocol.
    It can optionally compress the serialized data, and is thread safe.
    """
    serializer_id = 5  # never change this

    def dumpsCall(self, obj, method, vargs, kwargs):
        return dill.dumps((obj, method, vargs, kwargs), config.DILL_PROTOCOL_VERSION)

    def dumps(self, data):
        return dill.dumps(data, config.DILL_PROTOCOL_VERSION)

    def loadsCall(self, data):
        return dill.loads(data)

    def loads(self, data):
        return dill.loads(data)

    @classmethod
    def register_type_replacement(cls, object_type, replacement_function):
        def copyreg_function(obj):
            return replacement_function(obj).__reduce__()

        if object_type is type or not inspect.isclass(object_type):
            raise ValueError("refusing to register replacement for a non-type or the type 'type' itself")
        try:
            copyreg.pickle(object_type, copyreg_function)
        except TypeError:
            pass


class MarshalSerializer(SerializerBase):
    """(de)serializer that wraps the marshal serialization protocol."""
    serializer_id = 3  # never change this

    def dumpsCall(self, obj, method, vargs, kwargs):
        vargs = [self.convert_obj_into_marshallable(value) for value in vargs]
        kwargs = {key: self.convert_obj_into_marshallable(value) for key, value in kwargs.items()}
        return marshal.dumps((obj, method, vargs, kwargs))

    def dumps(self, data):
        return marshal.dumps(self.convert_obj_into_marshallable(data))

    if sys.platform == "cli":
        def loadsCall(self, data):
            if type(data) is not str:
                # Ironpython's marshal expects str...
                data = str(data)
            obj, method, vargs, kwargs = marshal.loads(data)
            vargs = self.recreate_classes(vargs)
            kwargs = self.recreate_classes(kwargs)
            return obj, method, vargs, kwargs

        def loads(self, data):
            if type(data) is not str:
                # Ironpython's marshal expects str...
                data = str(data)
            return self.recreate_classes(marshal.loads(data))
    else:
        def loadsCall(self, data):
            data = self._convertToBytes(data)
            obj, method, vargs, kwargs = marshal.loads(data)
            vargs = self.recreate_classes(vargs)
            kwargs = self.recreate_classes(kwargs)
            return obj, method, vargs, kwargs

        def loads(self, data):
            data = self._convertToBytes(data)
            return self.recreate_classes(marshal.loads(data))

    marshalable_types = (str, int, float, type(None), bool, complex, bytes, bytearray,
                         tuple, set, frozenset, list, dict)
    if sys.version_info < (3, 0):
        marshalable_types += (unicode,)

    def convert_obj_into_marshallable(self, obj):
        if isinstance(obj, self.marshalable_types):
            return obj
        if isinstance(obj, array.array):
            if obj.typecode == 'c':
                return obj.tostring()
            if obj.typecode == 'u':
                return obj.tounicode()
            return obj.tolist()
        return self.class_to_dict(obj)

    @classmethod
    def class_to_dict(cls, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super(MarshalSerializer, cls).class_to_dict(obj)

    @classmethod
    def register_type_replacement(cls, object_type, replacement_function):
        pass  # marshal serializer doesn't support per-type hooks


class SerpentSerializer(SerializerBase):
    """(de)serializer that wraps the serpent serialization protocol."""
    serializer_id = 1  # never change this

    def dumpsCall(self, obj, method, vargs, kwargs):
        return serpent.dumps((obj, method, vargs, kwargs), module_in_classname=True)

    def dumps(self, data):
        return serpent.dumps(data, module_in_classname=True)

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

        if object_type is type or not inspect.isclass(object_type):
            raise ValueError("refusing to register replacement for a non-type or the type 'type' itself")
        serpent.register_class(object_type, custom_serializer)

    @classmethod
    def dict_to_class(cls, data):
        if data.get("__class__") == "float":
            return float(data["value"])     # serpent encodes a float nan as a special class dict like this
        return super(SerpentSerializer, cls).dict_to_class(data)


class JsonSerializer(SerializerBase):
    """(de)serializer that wraps the json serialization protocol."""
    serializer_id = 2  # never change this

    __type_replacements = {}

    def dumpsCall(self, obj, method, vargs, kwargs):
        data = {"object": obj, "method": method, "params": vargs, "kwargs": kwargs}
        data = json.dumps(data, ensure_ascii=False, default=self.default)
        return data.encode("utf-8")

    def dumps(self, data):
        data = json.dumps(data, ensure_ascii=False, default=self.default)
        return data.encode("utf-8")

    def loadsCall(self, data):
        data = self._convertToBytes(data).decode("utf-8")
        data = json.loads(data)
        vargs = self.recreate_classes(data["params"])
        kwargs = self.recreate_classes(data["kwargs"])
        return data["object"], data["method"], vargs, kwargs

    def loads(self, data):
        data = self._convertToBytes(data).decode("utf-8")
        return self.recreate_classes(json.loads(data))

    def default(self, obj):
        replacer = self.__type_replacements.get(type(obj), None)
        if replacer:
            obj = replacer(obj)
        if isinstance(obj, set):
            return tuple(obj)  # json module can't deal with sets so we make a tuple out of it
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        if isinstance(obj, array.array):
            if obj.typecode == 'c':
                return obj.tostring()
            if obj.typecode == 'u':
                return obj.tounicode()
            return obj.tolist()
        return self.class_to_dict(obj)

    @classmethod
    def register_type_replacement(cls, object_type, replacement_function):
        if object_type is type or not inspect.isclass(object_type):
            raise ValueError("refusing to register replacement for a non-type or the type 'type' itself")
        cls.__type_replacements[object_type] = replacement_function


class MsgpackSerializer(SerializerBase):
    """(de)serializer that wraps the msgpack serialization protocol."""
    serializer_id = 6  # never change this

    __type_replacements = {}

    def dumpsCall(self, obj, method, vargs, kwargs):
        return msgpack.packb((obj, method, vargs, kwargs), use_bin_type=True, default=self.default)

    def dumps(self, data):
        return msgpack.packb(data, use_bin_type=True, default=self.default)

    def loadsCall(self, data):
        data = self._convertToBytes(data)
        obj, method, vargs, kwargs = msgpack.unpackb(data, raw=False, object_hook=self.object_hook)
        return obj, method, vargs, kwargs

    def loads(self, data):
        data = self._convertToBytes(data)
        return msgpack.unpackb(data, raw=False, object_hook=self.object_hook, ext_hook=self.ext_hook)

    def default(self, obj):
        replacer = self.__type_replacements.get(type(obj), None)
        if replacer:
            obj = replacer(obj)
        if isinstance(obj, set):
            return tuple(obj)  # msgpack module can't deal with sets so we make a tuple out of it
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, bytearray):
            return bytes(obj)
        if isinstance(obj, complex):
            return msgpack.ExtType(0x30, struct.pack("dd", obj.real, obj.imag))
        if isinstance(obj, datetime.datetime):
            if obj.tzinfo:
                raise errors.SerializeError("msgpack cannot serialize datetime with timezone info")
            return msgpack.ExtType(0x32, struct.pack("d", obj.timestamp()))
        if isinstance(obj, datetime.date):
            return msgpack.ExtType(0x33, struct.pack("l", obj.toordinal()))
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        if isinstance(obj, numbers.Number):
            return msgpack.ExtType(0x31, str(obj).encode("ascii"))     # long
        if isinstance(obj, array.array):
            if obj.typecode == 'c':
                return obj.tostring()
            if obj.typecode == 'u':
                return obj.tounicode()
            return obj.tolist()
        return self.class_to_dict(obj)

    def object_hook(self, obj):
        if "__class__" in obj:
            return self.dict_to_class(obj)
        return obj

    def ext_hook(self, code, data):
        if code == 0x30:
            real, imag = struct.unpack("dd", data)
            return complex(real, imag)
        if code == 0x31:
            return int(data)
        if code == 0x32:
            return datetime.datetime.fromtimestamp(struct.unpack("d", data)[0])
        if code == 0x33:
            return datetime.date.fromordinal(struct.unpack("l", data)[0])
        raise errors.SerializeError("invalid ext code for msgpack: " + str(code))

    @classmethod
    def register_type_replacement(cls, object_type, replacement_function):
        if object_type is type or not inspect.isclass(object_type):
            raise ValueError("refusing to register replacement for a non-type or the type 'type' itself")
        cls.__type_replacements[object_type] = replacement_function


"""The various serializers that are supported"""
_serializers = {}
_serializers_by_id = {}


def get_serializer(name):
    try:
        return _serializers[name]
    except KeyError:
        raise errors.SerializeError("serializer '%s' is unknown or not available" % name)


def get_serializer_by_id(sid):
    try:
        return _serializers_by_id[sid]
    except KeyError:
        raise errors.SerializeError("no serializer available for id %d" % sid)


# determine the serializers that are supported
try:
    import cPickle as pickle
except ImportError:
    import pickle
assert config.PICKLE_PROTOCOL_VERSION >= 2, "pickle protocol needs to be 2 or higher"
_ser = PickleSerializer()
_serializers["pickle"] = _ser
_serializers_by_id[_ser.serializer_id] = _ser
import marshal
_ser = MarshalSerializer()
_serializers["marshal"] = _ser
_serializers_by_id[_ser.serializer_id] = _ser
try:
    import cloudpickle
    _ser = CloudpickleSerializer()
    _serializers["cloudpickle"] = _ser
    _serializers_by_id[_ser.serializer_id] = _ser
except ImportError:
    pass
try:
    import dill
    _ser = DillSerializer()
    _serializers["dill"] = _ser
    _serializers_by_id[_ser.serializer_id] = _ser
except ImportError:
    pass
try:
    try:
        import importlib
        json = importlib.import_module(config.JSON_MODULE)
    except ImportError:
        json = __import__(config.JSON_MODULE)
    _ser = JsonSerializer()
    _serializers["json"] = _ser
    _serializers_by_id[_ser.serializer_id] = _ser
except ImportError:
    pass
try:
    import serpent
    _ser = SerpentSerializer()
    _serializers["serpent"] = _ser
    _serializers_by_id[_ser.serializer_id] = _ser
except ImportError:
    log.warning("serpent serializer is not available")
try:
    import msgpack
    _ser = MsgpackSerializer()
    _serializers["msgpack"] = _ser
    _serializers_by_id[_ser.serializer_id] = _ser
except ImportError:
    pass
del _ser


def getAttribute(obj, attr):
    """
    Resolves an attribute name to an object.  Raises
    an AttributeError if any attribute in the chain starts with a '``_``'.
    Doesn't resolve a dotted name, because that is a security vulnerability.
    It treats it as a single attribute name (and the lookup will likely fail).
    """
    if is_private_attribute(attr):
        raise AttributeError("attempt to access private attribute '%s'" % attr)
    else:
        obj = getattr(obj, attr)
    if not config.REQUIRE_EXPOSE or getattr(obj, "_pyroExposed", False):
        return obj
    raise AttributeError("attempt to access unexposed attribute '%s'" % attr)


def excepthook(ex_type, ex_value, ex_tb):
    """An exception hook you can use for ``sys.excepthook``, to automatically print remote Pyro tracebacks"""
    traceback = "".join(getPyroTraceback(ex_type, ex_value, ex_tb))
    sys.stderr.write(traceback)


def fixIronPythonExceptionForPickle(exceptionObject, addAttributes):
    """
    Function to hack around a bug in IronPython where it doesn't pickle
    exception attributes. We piggyback them into the exception's args.
    Bug report is at https://github.com/IronLanguages/main/issues/943
    Bug is still present in Ironpython 2.7.7
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


__exposed_member_cache = {}


def reset_exposed_members(obj, only_exposed=True, as_lists=False):
    """Delete any cached exposed members forcing recalculation on next request"""
    if not inspect.isclass(obj):
        obj = obj.__class__
    cache_key = (obj, only_exposed, as_lists)
    __exposed_member_cache.pop(cache_key, None)


def get_exposed_members(obj, only_exposed=True, as_lists=False, use_cache=True):
    """
    Return public and exposed members of the given object's class.
    You can also provide a class directly.
    Private members are ignored no matter what (names starting with underscore).
    If only_exposed is True, only members tagged with the @expose decorator are
    returned. If it is False, all public members are returned.
    The return value consists of the exposed methods, exposed attributes, and methods
    tagged as @oneway.
    (All this is used as meta data that Pyro sends to the proxy if it asks for it)
    as_lists is meant for python 2 compatibility.
    """
    if not inspect.isclass(obj):
        obj = obj.__class__

    cache_key = (obj, only_exposed, as_lists)
    if use_cache and cache_key in __exposed_member_cache:
        return __exposed_member_cache[cache_key]

    methods = set()  # all methods
    oneway = set()  # oneway methods
    attrs = set()  # attributes
    for m in dir(obj):      # also lists names inherited from super classes
        if is_private_attribute(m):
            continue
        v = getattr(obj, m)
        if inspect.ismethod(v) or inspect.isfunction(v) or inspect.ismethoddescriptor(v):
            if getattr(v, "_pyroExposed", not only_exposed):
                methods.add(m)
                # check if the method is marked with the 'oneway' decorator:
                if getattr(v, "_pyroOneway", False):
                    oneway.add(m)
        elif inspect.isdatadescriptor(v):
            func = getattr(v, "fget", None) or getattr(v, "fset", None) or getattr(v, "fdel", None)
            if func is not None and getattr(func, "_pyroExposed", not only_exposed):
                attrs.add(m)
        # Note that we don't expose plain class attributes no matter what.
        # it is a syntax error to add a decorator on them, and it is not possible
        # to give them a _pyroExposed tag either.
        # The way to expose attributes is by using properties for them.
        # This automatically solves the protection/security issue: you have to
        # explicitly decide to make an attribute into a @property (and to @expose it
        # if REQUIRE_EXPOSED=True) before it is remotely accessible.
    if as_lists:
        methods = list(methods)
        oneway = list(oneway)
        attrs = list(attrs)
    result = {
        "methods": methods,
        "oneway": oneway,
        "attrs": attrs
    }
    __exposed_member_cache[cache_key] = result
    return result


def get_exposed_property_value(obj, propname, only_exposed=True):
    """
    Return the value of an @exposed @property.
    If the requested property is not a @property or not exposed,
    an AttributeError is raised instead.
    """
    v = getattr(obj.__class__, propname)
    if inspect.isdatadescriptor(v):
        if v.fget and getattr(v.fget, "_pyroExposed", not only_exposed):
            return v.fget(obj)
    raise AttributeError("attempt to access unexposed or unknown remote attribute '%s'" % propname)


def set_exposed_property_value(obj, propname, value, only_exposed=True):
    """
    Sets the value of an @exposed @property.
    If the requested property is not a @property or not exposed,
    an AttributeError is raised instead.
    """
    v = getattr(obj.__class__, propname)
    if inspect.isdatadescriptor(v):
        pfunc = v.fget or v.fset or v.fdel
        if v.fset and getattr(pfunc, "_pyroExposed", not only_exposed):
            return v.fset(obj, value)
    raise AttributeError("attempt to access unexposed or unknown remote attribute '%s'" % propname)


_private_dunder_methods = frozenset([
    "__init__", "__init_subclass__", "__class__", "__module__", "__weakref__",
    "__call__", "__new__", "__del__", "__repr__", "__unicode__",
    "__str__", "__format__", "__nonzero__", "__bool__", "__coerce__",
    "__cmp__", "__eq__", "__ne__", "__hash__", "__ge__", "__gt__", "__le__", "__lt__",
    "__dir__", "__enter__", "__exit__", "__copy__", "__deepcopy__", "__sizeof__",
    "__getattr__", "__setattr__", "__hasattr__", "__getattribute__", "__delattr__",
    "__instancecheck__", "__subclasscheck__", "__getinitargs__", "__getnewargs__",
    "__getstate__", "__setstate__", "__reduce__", "__reduce_ex__",
    "__getstate_for_dict__", "__setstate_from_dict__", "__subclasshook__"
])


def is_private_attribute(attr_name):
    """returns if the attribute name is to be considered private or not."""
    if attr_name in _private_dunder_methods:
        return True
    if not attr_name.startswith('_'):
        return False
    if len(attr_name) > 4 and attr_name.startswith("__") and attr_name.endswith("__"):
        return False
    return True
