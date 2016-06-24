"""
Pyro serializers
Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import marshal
import importlib
import logging
import zlib
import Pyro4
import sys

log = logging.getLogger("Pyro4.serializers")


if sys.version_info < (3, 0):
    import exceptions
else:
    import builtins

try:
    import copyreg
except ImportError:
    import copy_reg as copyreg
try:
    import cPickle as pickle
except ImportError:
    import pickle
try:
    try:
        json = importlib.import_module(Pyro4.config.JSON_MODULE)
    except ImportError:
        json = __import__(Pyro4.config.JSON_MODULE)
except ImportError:
    log.warning("json serializer is not available")
    json = None
try:
    if platform.python_implementation() in ('PyPy', 'IronPython'):
        raise ImportError('Currently dill is not supported with IronPython and PyPy')
    import dill
except ImportError:
    log.warning("dill serializer is not available")
    dill = None
try:
    import serpent
except ImportError:
    log.warning("serpent serializer is not available")
    serpent = None

assert Pyro4.config.PICKLE_PROTOCOL_VERSION >= 2, "pickle protocol needs to be 2 or higher"


"""The various serializers that are supported"""
_serializers = {}
_serializers_by_id = {}
_serializers_by_classname = {}


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

    def __compressdata(self, data, compress):
        if not compress or len(data) < 200:
            return data, False  # don't waste time compressing small messages
        compressed = zlib.compress(data)
        if len(compressed) < len(data):
            return compressed, True
        return data, False

    @classmethod
    def decompress_if_needed(cls, message):
        if message.flags & Pyro4.message.FLAGS_COMPRESSED:
            message.data = zlib.decompress(message.data)
            message.flags &= ~Pyro4.message.FLAGS_COMPRESSED
        return message

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
                import serpent

                def serpent_converter(obj, serializer, stream, level):
                    d = converter(obj)
                    serializer.ser_builtins_dict(d, stream, level)

                serpent.register_class(clazz, serpent_converter)
            except Pyro4.errors.ProtocolError:
                pass

    @classmethod
    def unregister_class_to_dict(cls, clazz):
        """Removes the to-dict conversion function registered for the given class. Objects of the class
        will be serialized by the default mechanism again."""
        if clazz in cls.__custom_class_to_dict_registry:
            del cls.__custom_class_to_dict_registry[clazz]
        try:
            get_serializer_by_id(SerpentSerializer.serializer_id)
            import serpent
            serpent.unregister_class(clazz)
        except Pyro4.errors.ProtocolError:
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
                raise Pyro4.errors.SerializeError("don't know how to serialize class " + str(obj.__class__) + " using serializer " + str(cls.__name__) + ". Give it vars() or an appropriate __getstate__")

    @classmethod
    def dict_to_class(cls, data):
        """
        Recreate an object out of a dict containing the class name and the attributes.
        Only a fixed set of classes are recognized.
        Not used for the pickle serializer.
        """
        classname = data.get("__class__", "<unknown>")
        if isinstance(classname, bytes):
            classname = classname.decode("utf-8")
        if classname in cls.__custom_dict_to_class_registry:
            converter = cls.__custom_dict_to_class_registry[classname]
            return converter(classname, data)
        if "__" in classname:
            raise Pyro4.errors.SecurityError("refused to deserialize types with double underscores in their name: " + classname)
        # because of efficiency reasons the constructors below are hardcoded here instead of added on a per-class basis to the dict-to-class registry
        if classname.startswith("Pyro4.core."):
            if classname == "Pyro4.core.URI":
                uri = Pyro4.core.URI.__new__(Pyro4.core.URI)
                uri.__setstate_from_dict__(data["state"])
                return uri
            elif classname == "Pyro4.core.Proxy":
                proxy = Pyro4.core.Proxy.__new__(Pyro4.core.Proxy)
                proxy.__setstate_from_dict__(data["state"])
                return proxy
            elif classname == "Pyro4.core.Daemon":
                daemon = Pyro4.core.Daemon.__new__(Pyro4.core.Daemon)
                daemon.__setstate_from_dict__(data["state"])
                return daemon
        elif (
            classname.startswith("Pyro4.serializers.") or
            classname.startswith("Pyro4.utils.")
        ):
            return get_serializer_by_class(classname)
        elif classname.startswith("Pyro4.errors."):
            errortype = getattr(Pyro4.errors, classname.split('.', 2)[2])
            if issubclass(errortype, Pyro4.errors.PyroError):
                return SerializerBase.make_exception(errortype, data)
        elif classname == "Pyro4.futures._ExceptionWrapper":
            ex = SerializerBase.dict_to_class(data["exception"])
            return Pyro4.futures._ExceptionWrapper(ex)
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

        # try one of the serializer classes
        for serializer in _serializers.values():
            if classname == serializer.__class__.__name__:
                return serializer
        log.warning("unsupported serialized class: " + classname)
        raise Pyro4.errors.SerializeError("unsupported serialized class: " + classname)

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
    serializer_id = Pyro4.message.SERIALIZER_PICKLE

    def dumpsCall(self, obj, method, vargs, kwargs):
        return pickle.dumps((obj, method, vargs, kwargs), Pyro4.config.PICKLE_PROTOCOL_VERSION)

    def dumps(self, data):
        return pickle.dumps(data, Pyro4.config.PICKLE_PROTOCOL_VERSION)

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


class DillSerializer(SerializerBase):
    """
    A (de)serializer that wraps the Dill serialization protocol.
    It can optionally compress the serialized data, and is thread safe.
    """
    serializer_id = Pyro4.message.SERIALIZER_DILL

    def dumpsCall(self, obj, method, vargs, kwargs):
        return dill.dumps((obj, method, vargs, kwargs), Pyro4.config.DILL_PROTOCOL_VERSION)

    def dumps(self, data):
        return dill.dumps(data, Pyro4.config.DILL_PROTOCOL_VERSION)

    def loadsCall(self, data):
        return dill.loads(data)

    def loads(self, data):
        return dill.loads(data)

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

    if sys.platform == "cli":
        def loads(self, data):
            if type(data) is not str:
                # Ironpython's marshal expects str...
                data = str(data)
            return self.recreate_classes(marshal.loads(data))
    else:
        def loads(self, data):
            return self.recreate_classes(marshal.loads(data))

    @classmethod
    def register_type_replacement(cls, object_type, replacement_function):
        pass  # marshal serializer doesn't support per-type hooks


class SerpentSerializer(SerializerBase):
    """(de)serializer that wraps the serpent serialization protocol."""
    serializer_id = Pyro4.message.SERIALIZER_SERPENT

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
        data = data.decode("utf-8")
        data = json.loads(data)
        vargs = self.recreate_classes(data["params"])
        kwargs = self.recreate_classes(data["kwargs"])
        return data["object"], data["method"], vargs, kwargs

    def loads(self, data):
        data = data.decode("utf-8")
        return self.recreate_classes(json.loads(data))

    def default(self, obj):
        replacer = self.__type_replacements.get(type(obj), None)
        if replacer:
            obj = replacer(obj)
        if isinstance(obj, set):
            return tuple(obj)  # json module can't deal with sets so we make a tuple out of it
        return self.class_to_dict(obj)

    @classmethod
    def register_type_replacement(cls, object_type, replacement_function):
        cls.__type_replacements[object_type] = replacement_function


def get_serializer(name):
    global _serializers
    try:
        return _serializers[name]
    except KeyError:
        raise Pyro4.errors.SerializeError("serializer '%s' is unknown or not available" % name)


def get_serializer_by_id(sid):
    global _serializers_by_id
    try:
        return _serializers_by_id[sid]
    except KeyError:
        raise Pyro4.errors.SerializeError("no serializer available for id %d" % sid)


def get_serializer_by_class(classname_with_package):
    global _serializers_by_classname
    return _serializers_by_classname[classname_with_package]


def register_serializer(name, serializer):
    global _serializers
    global _serializers_by_id
    global _serializers_by_classname
    if name in _serializers:
        raise ValueError("serializer {} already registered".format(name))
    if serializer.serializer_id in _serializers_by_id:
        raise ValueError("serializer {} id={} already registerd".format(
            name, serializer.serializer_id))
    classname_with_package = "Pyro4.serializers.{}".format(
        serializer.__class__.__name__)
    _serializers[name] = serializer
    _serializers_by_id[serializer.serializer_id] = serializer
    _serializers_by_classname[classname_with_package] = serializer


all_exceptions = {}
if sys.version_info < (3, 0):
    for name, t in vars(exceptions).items():
        if type(t) is type and issubclass(t, BaseException):
            all_exceptions[name] = t
else:
    for name, t in vars(builtins).items():
        if type(t) is type and issubclass(t, BaseException):
            all_exceptions[name] = t
for name, t in vars(Pyro4.errors).items():
    if type(t) is type and issubclass(t, Pyro4.errors.PyroError):
        all_exceptions[name] = t


register_serializer("pickle", PickleSerializer())
register_serializer("marshal", MarshalSerializer())
if dill is not None:
    register_serializer("dill", DillSerializer())
if json is not None:
    register_serializer("json", JsonSerializer())
if serpent is not None:
    if '-' in serpent.__version__:
        ver = serpent.__version__.split('-', 1)[0]
    else:
        ver = serpent.__version__
    ver = tuple(map(int, ver.split(".")))
    if ver < (1, 11):
        raise RuntimeError("requires serpent 1.11 or better")
    register_serializer("serpent", SerpentSerializer())
