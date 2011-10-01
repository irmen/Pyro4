"""
Flame support:  Foreign Location Automatic Module Exposer.
Easy but potentially dangerous exposing of remote modules.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import sys
import types
import inspect
import Pyro4.core
import Pyro4.util
try:
    import importlib
except ImportError:
    importlib=None
try:
    import builtins
except ImportError:
    import __builtin__ as builtins

__all__=["FlameServer","FlameModule","FlameBuiltin"]


# Exec is a statement in Py2, a function in Py3
# Workaround as written by Ned Batchelder on his blog.
if sys.version_info>(3,0):
    def exec_function(source, filename, global_map):
        exec(compile(source, filename, "exec"), global_map)
else:
    # OK, this is pretty gross.  In Py2, exec was a statement, but that will
    # be a syntax error if we try to put it in a Py3 file, even if it isn't
    # executed.  So hide it inside an evaluated string literal instead.
    eval(compile("""\
def exec_function(source, filename, global_map):
    exec compile(source, filename, "exec") in global_map
""",
    "<exec_function>", "exec"
    ))


class FlameModule(object):
    def __init__(self, flameserver, module):
        # store a proxy to the flameserver regardless of autoproxy setting
        self.flameserver=Pyro4.core.Proxy(flameserver._pyroDaemon.uriFor(flameserver))
        self.module=module
    def __getattr__(self, item):
        if item in ("__getnewargs__","__getinitargs__"):
            raise AttributeError(item)
        return Pyro4.core._RemoteMethod(self.__invoke, "%s.%s" % (self.module, item))
    def __getstate__(self):
        return self.__dict__
    def __setstate__(self, args):
        self.__dict__=args
    def __invoke(self, module, args, kwargs):
        return self.flameserver._invokeModule(module, args,kwargs)
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.flameserver._pyroRelease()
    def __repr__(self):
        return "<%s.%s at 0x%x, module '%s' at %s>" % (self.__class__.__module__, self.__class__.__name__,
            id(self), self.module, self.flameserver._pyroUri.location)


class FlameBuiltin(object):
    def __init__(self, flameserver, builtin):
        # store a proxy to the flameserver regardless of autoproxy setting
        self.flameserver=Pyro4.core.Proxy(flameserver._pyroDaemon.uriFor(flameserver))
        self.builtin=builtin
    def __call__(self, *args, **kwargs):
        return self.flameserver._invokeBuiltin(self.builtin, args, kwargs)
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.flameserver._pyroRelease()
    def __repr__(self):
        return "<%s.%s at 0x%x, builtin '%s' at %s>" % (self.__class__.__module__, self.__class__.__name__,
            id(self), self.builtin, self.flameserver._pyroUri.location)


class FlameServer(object):
    """
    FLAME (Foreign Location Automatic Module Exposer) server.
    Usually created by using :py:meth:`Pyro4.core.Daemon.startFlame`.
    Be *very* cautious before starting this: it allows the clients full access to everything on your system.
    """
    def module(self, name):
        """import a module given by the module name and return a proxy for it"""
        if importlib:
            m=importlib.import_module(name)
        else:
            m=__import__(name)
        return FlameModule(self, name)

    def builtin(self, name):
        """returns a proxy for the given builtin"""
        return FlameBuiltin(self, name)

    def execute(self, code):
        """execute a piece of code"""
        exec_function(code, "<remote-code>", globals())

    def evaluate(self, expression):
        """evaluate an expression and return its result"""
        return eval(expression)

    def sendmodule(self, modulename, modulesource):
        """send the source of a module to the server and make it import it"""
        module=types.ModuleType(modulename)
        exec_function(modulesource, "<remote-module>", module.__dict__)
        sys.modules[modulename]=module

    def getmodule(self, modulename):
        """obtain the source code from a module"""
        module=__import__(modulename, globals={}, locals={})
        return inspect.getsource(module)

    def _invokeBuiltin(self, builtin, args, kwargs):
        return getattr(builtins, builtin)(*args, **kwargs)

    def _invokeModule(self, dottedname, args, kwargs):
        # dottedname is something like "os.path.walk" so strip off the module name
        modulename, dottedname=dottedname.split('.',1)
        module=sys.modules[modulename]
        # we override the DOTTEDNAMES setting here because this safeguard makes no sense
        # with the Flame server (if enabled it already allows full access to anything):
        method=Pyro4.util.resolveDottedAttribute(module, dottedname, True)
        return method(*args, **kwargs)
