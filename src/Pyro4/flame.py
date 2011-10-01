"""
Pyro FLAME:  Foreign Location Automatic Module Exposer.
Easy but potentially very dangerous way of exposing remote modules and builtins.

You can start this module as a script from the command line, to easily get a
flame server running:

  :command:`python -m Pyro4.flame`

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import sys
import types
import inspect
import Pyro4.core
import Pyro4.util
import Pyro4.constants
try:
    import importlib
except ImportError:
    importlib=None
try:
    import builtins
except ImportError:
    import __builtin__ as builtins

__all__=["connect","Flame"]


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
    """
    Proxy to a remote module.
    """
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
    """
    Proxy to a remote builtin function.
    """
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


class Flame(object):
    """
    The actual FLAME server logic.
    Usually created by using :py:meth:`Pyro4.core.Daemon.startFlame`.
    Be *very* cautious before starting this: it allows the clients full access to everything on your system.
    """
    def module(self, name):
        """import a module on the server given by the module name and returns a proxy to it"""
        if importlib:
            m=importlib.import_module(name)
        else:
            m=__import__(name)
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
        """send the source of a module to the server and make it import it"""
        module=types.ModuleType(modulename)
        exec_function(modulesource, "<remote-module>", module.__dict__)
        sys.modules[modulename]=module

    def getmodule(self, modulename):
        """obtain the source code from a module available on the server"""
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


def connect(location):
    """
    Connect to a Flame server on the given location, for instance localhost:9999 or ./u:unixsock
    This is just a convenience function to creates an appropriate Pyro proxy.
    """
    return Pyro4.core.Proxy("PYRO:%s@%s" % (Pyro4.constants.FLAME_NAME, location))


def main(args, returnWithoutLooping=False):
    from optparse import OptionParser
    parser=OptionParser()
    parser.add_option("-H","--host", default="localhost", help="hostname to bind server on (default=localhost)")
    parser.add_option("-p","--port", type="int", default=0, help="port to bind server on")
    parser.add_option("-u","--unixsocket", help="Unix domain socket name to bind server on")
    parser.add_option("-q","--quiet", action="store_true", default=False, help="don't output anything")
    parser.add_option("-k","--key", help="the HMAC key to use (required)")
    options,args = parser.parse_args(args)

    if not options.quiet:
        print("Starting Pyro Flame server.")

    hmac=options.key
    if not hmac:
        print("Warning: HMAC key not set. Anyone can connect to this server!")
    if hmac and sys.version_info>=(3,0):
        hmac=bytes(hmac,"utf-8")
    Pyro4.config.HMAC_KEY=hmac or Pyro4.config.HMAC_KEY
    if not options.quiet and Pyro4.config.HMAC_KEY:
        print("HMAC_KEY set to: %s" % Pyro4.config.HMAC_KEY)

    d=Pyro4.core.Daemon(host=options.host, port=options.port, unixsocket=options.unixsocket)
    uri=d.startFlame()
    if not options.quiet:
        print("server uri: %s" % uri)
        print("server is running.")

    if returnWithoutLooping:
        return d,uri        # for unit testing
    else:
        d.requestLoop()
    d.close()
    return 0

if __name__=="__main__":
    sys.exit(main(sys.argv[1:]))
