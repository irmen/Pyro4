"""
Pyro FLAME:  Foreign Location Automatic Module Exposer.
Easy but potentially very dangerous way of exposing remote modules and builtins.
Flame requires the pickle serializer to be used.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import sys
import types
import code
import os
import stat
import Pyro4.core
import Pyro4.util
import Pyro4.constants
import Pyro4.errors

try:
    import importlib
except ImportError:
    importlib = None
try:
    import builtins
except ImportError:
    import __builtin__ as builtins
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

__all__ = ["connect", "start", "createModule", "Flame"]


# Exec is a statement in Py2, a function in Py3
# Workaround as written by Ned Batchelder on his blog.
if sys.version_info > (3, 0):
    def exec_function(source, filename, global_map):
        source = fixExecSourceNewlines(source)
        exec(compile(source, filename, "exec"), global_map)
else:
    # OK, this is pretty gross.  In Py2, exec was a statement, but that will
    # be a syntax error if we try to put it in a Py3 file, even if it isn't
    # executed.  So hide it inside an evaluated string literal instead.
    eval(compile("""\
def exec_function(source, filename, global_map):
    source=fixExecSourceNewlines(source)
    exec compile(source, filename, "exec") in global_map
""", "<exec_function>", "exec"))


def fixExecSourceNewlines(source):
    if sys.version_info < (2, 7) or sys.version_info[:2] in ((3, 0), (3, 1)):
        # for python versions prior to 2.7 (and 3.0/3.1), compile is kinda picky.
        # it needs unix type newlines and a trailing newline to work correctly.
        source = source.replace("\r\n", "\n")
        source = source.rstrip() + "\n"
    # remove trailing whitespace that might cause IndentationErrors
    source = source.rstrip()
    return source


class FlameModule(object):
    """Proxy to a remote module."""

    def __init__(self, flameserver, module):
        # store a proxy to the flameserver regardless of autoproxy setting
        self.flameserver = Pyro4.core.Proxy(flameserver._pyroDaemon.uriFor(flameserver))
        self.module = module

    def __getattr__(self, item):
        if item in ("__getnewargs__", "__getnewargs_ex__", "__getinitargs__"):
            raise AttributeError(item)
        return Pyro4.core._RemoteMethod(self.__invoke, "%s.%s" % (self.module, item), 0)

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, args):
        self.__dict__ = args

    def __invoke(self, module, args, kwargs):
        return self.flameserver.invokeModule(module, args, kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.flameserver._pyroRelease()

    def __repr__(self):
        return "<%s.%s at 0x%x, module '%s' at %s>" % (self.__class__.__module__, self.__class__.__name__,
                                                       id(self), self.module, self.flameserver._pyroUri.location)


class FlameBuiltin(object):
    """Proxy to a remote builtin function."""

    def __init__(self, flameserver, builtin):
        # store a proxy to the flameserver regardless of autoproxy setting
        self.flameserver = Pyro4.core.Proxy(flameserver._pyroDaemon.uriFor(flameserver))
        self.builtin = builtin

    def __call__(self, *args, **kwargs):
        return self.flameserver.invokeBuiltin(self.builtin, args, kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.flameserver._pyroRelease()

    def __repr__(self):
        return "<%s.%s at 0x%x, builtin '%s' at %s>" % (self.__class__.__module__, self.__class__.__name__,
                                                        id(self), self.builtin, self.flameserver._pyroUri.location)


class RemoteInteractiveConsole(object):
    """Proxy to a remote interactive console."""

    class LineSendingConsole(code.InteractiveConsole):
        """makes sure the lines are sent to the remote console"""

        def __init__(self, remoteconsole):
            code.InteractiveConsole.__init__(self, filename="<remoteconsole>")
            self.remoteconsole = remoteconsole

        def push(self, line):
            output, more = self.remoteconsole.push_and_get_output(line)
            if output:
                sys.stdout.write(output)
            return more

    def __init__(self, remoteconsoleuri):
        # store a proxy to the console regardless of autoproxy setting
        self.remoteconsole = Pyro4.core.Proxy(remoteconsoleuri)

    def interact(self):
        console = self.LineSendingConsole(self.remoteconsole)
        console.interact(banner=self.remoteconsole.get_banner())
        print("(Remote session ended)")

    def close(self):
        self.remoteconsole.terminate()
        self.remoteconsole._pyroRelease()

    def terminate(self):
        self.close()

    def __repr__(self):
        return "<%s.%s at 0x%x, for %s>" % (self.__class__.__module__, self.__class__.__name__,
                                            id(self), self.remoteconsole._pyroUri.location)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class InteractiveConsole(code.InteractiveConsole):
    """Interactive console wrapper that saves output written to stdout so it can be returned as value"""

    def push_and_get_output(self, line):
        output, more = "", False
        stdout_save = sys.stdout
        try:
            sys.stdout = StringIO()
            more = self.push(line)
            output = sys.stdout.getvalue()
            sys.stdout.close()
        finally:
            sys.stdout = stdout_save
        return output, more

    def get_banner(self):
        return self.banner  # custom banner string, set by Pyro daemon

    def write(self, data):
        sys.stdout.write(data)  # stdout instead of stderr

    def terminate(self):
        self._pyroDaemon.unregister(self)
        self.resetbuffer()


@Pyro4.expose
class Flame(object):
    """
    The actual FLAME server logic.
    Usually created by using :py:meth:`Pyro4.core.Daemon.startFlame`.
    Be *very* cautious before starting this: it allows the clients full access to everything on your system.
    """

    def __init__(self):
        if set(Pyro4.config.SERIALIZERS_ACCEPTED) != set(["pickle"]):
            raise RuntimeError("flame requires the pickle serializer exclusively")

    def module(self, name):
        """import a module on the server given by the module name and returns a proxy to it"""
        if importlib:
            importlib.import_module(name)
        else:
            __import__(name)
        return FlameModule(self, name)

    def builtin(self, name):
        """returns a proxy to the given builtin on the server"""
        return FlameBuiltin(self, name)

    def execute(self, code):
        """execute a piece of code"""
        exec_function(code, "<remote-code>", globals())

    def evaluate(self, expression):
        """evaluate an expression and return its result"""
        return eval(expression)

    def sendmodule(self, modulename, modulesource):
        """
        Send the source of a module to the server and make the server load it.
        Note that you still have to actually ``import`` it on the server to access it.
        Sending a module again will replace the previous one with the new.
        """
        createModule(modulename, modulesource)

    def getmodule(self, modulename):
        """obtain the source code from a module on the server"""
        import inspect
        module = __import__(modulename, globals={}, locals={})
        return inspect.getsource(module)

    def sendfile(self, filename, filedata):
        """store a new file on the server"""
        with open(filename, "wb") as targetfile:
            os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR)  # readable/writable by owner only
            targetfile.write(filedata)

    def getfile(self, filename):
        """read any accessible file from the server"""
        with open(filename, "rb") as diskfile:
            return diskfile.read()

    def console(self):
        """get a proxy for a remote interactive console session"""
        console = InteractiveConsole(filename="<remoteconsole>")
        uri = self._pyroDaemon.register(console)
        console.banner = "Python %s on %s\n(Remote console on %s)" % (sys.version, sys.platform, uri.location)
        return RemoteInteractiveConsole(uri)

    @Pyro4.expose
    def invokeBuiltin(self, builtin, args, kwargs):
        return getattr(builtins, builtin)(*args, **kwargs)

    @Pyro4.expose
    def invokeModule(self, dottedname, args, kwargs):
        # dottedname is something like "os.path.walk" so strip off the module name
        modulename, dottedname = dottedname.split('.', 1)
        module = sys.modules[modulename]
        # Look up the actual method to call.
        # Because Flame already opens all doors, security wise, we allow ourselves to
        # look up a dotted name via object traversal. The security implication of that
        # is overshadowed by the security implications of enabling Flame in the first place.
        # We also don't check for access to 'private' methods. Same reasons.
        method = module
        for attr in dottedname.split('.'):
            method = getattr(method, attr)
        return method(*args, **kwargs)


def createModule(name, source, filename="<dynamic-module>", namespace=None):
    """
    Utility function to create a new module with the given name (dotted notation allowed), directly from the source string.
    Adds it to sys.modules, and returns the new module object.
    If you provide a namespace dict (such as ``globals()``), it will import the module into that namespace too.
    """
    path = ""
    components = name.split('.')
    module = types.ModuleType("pyro-flame-module-context")
    for component in components:
        # build the module hierarchy.
        path += '.' + component
        real_path = path[1:]
        if real_path in sys.modules:
            # use already loaded modules instead of overwriting them
            module = sys.modules[real_path]
        else:
            setattr(module, component, types.ModuleType(real_path))
            module = getattr(module, component)
            sys.modules[real_path] = module
    exec_function(source, filename, module.__dict__)
    if namespace is not None:
        namespace[components[0]] = __import__(name)
    return module


def start(daemon):
    """
    Create and register a Flame server in the given daemon.
    Be *very* cautious before starting this: it allows the clients full access to everything on your system.
    """
    if Pyro4.config.FLAME_ENABLED:
        if set(Pyro4.config.SERIALIZERS_ACCEPTED) != set(["pickle"]):
            raise Pyro4.errors.SerializeError("Flame requires the pickle serializer exclusively")
        return daemon.register(Flame(), Pyro4.constants.FLAME_NAME)
    else:
        raise Pyro4.errors.SecurityError("Flame is disabled in the server configuration")


def connect(location):
    """
    Connect to a Flame server on the given location, for instance localhost:9999 or ./u:unixsock
    This is just a convenience function to creates an appropriate Pyro proxy.
    """
    if Pyro4.config.SERIALIZER != "pickle":
        raise Pyro4.errors.SerializeError("Flame requires the pickle serializer")
    proxy = Pyro4.core.Proxy("PYRO:%s@%s" % (Pyro4.constants.FLAME_NAME, location))
    proxy._pyroBind()
    return proxy
