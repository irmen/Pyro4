"""
Miscellaneous utilities
Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import sys
import logging
import linecache
import traceback
import inspect
import Pyro4
import Pyro4.errors
import Pyro4.message
from Pyro4.serializers import json  # noqa

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
        local_tb = formatTraceback(ex_type, ex_value, ex_tb, Pyro4.config.DETAILED_TRACEBACK)
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
    if not Pyro4.config.REQUIRE_EXPOSE or getattr(obj, "_pyroExposed", False):
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
    Bug report is at http://ironpython.codeplex.com/workitem/30805
    migrated to github as https://github.com/IronLanguages/main/issues/943
    Bug is still present in Ironpython 2.7.5
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


def get_exposed_members(obj, only_exposed=True, as_lists=False):
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
    methods = set()  # all methods
    oneway = set()  # oneway methods
    attrs = set()  # attributes
    for m in dir(obj):      # also lists names inherited from super classes
        if is_private_attribute(m):
            continue
        v = getattr(obj, m)
        if inspect.ismethod(v) or inspect.isfunction(v):
            if getattr(v, "_pyroExposed", not only_exposed):
                methods.add(m)
                # check if the method is marked with the @Pyro4.oneway decorator:
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
    return {
        "methods": methods,
        "oneway": oneway,
        "attrs": attrs
    }


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
    "__init__", "__call__", "__new__", "__del__", "__repr__", "__unicode__",
    "__str__", "__format__", "__nonzero__", "__bool__", "__coerce__",
    "__cmp__", "__eq__", "__ne__", "__hash__",
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
