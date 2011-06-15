# This is the remote input/output server
from __future__ import print_function
import sys
import Pyro4

if sys.version_info<(3,0):
    input=raw_input

class RemoteIOManager(object):
    """The Pyro object that provides the remote in/out stream proxies"""
    def __init__(self, stdin_uri, stdout_uri):
        self.stdin_uri=stdin_uri
        self.stdout_uri=stdout_uri
    def getInputOutput(self):
        return Pyro4.Proxy(self.stdout_uri), Pyro4.Proxy(self.stdin_uri)


class SimpleProxy(object):
    """simple proxy to another object.
    Needed to be able to use built-in types as a remote Pyro object"""
    def __init__(self, open_file):
        #self._obj=open_file
        object.__setattr__(self, "_obj", open_file)
    def __getattribute__(self, name):
        if name=="fileno":
            # hack to make it work on Python 3.x
            raise AttributeError(name)
        elif name.startswith("_pyro"):
            # little hack to get Pyro's attributes from this object itself
            return object.__getattribute__(self, name)
        else:
            # all other attributes and methods are passed to the proxied _obj
            return getattr(object.__getattribute__(self, "_obj"), name)


d=Pyro4.Daemon()
stdin_uri=d.register(SimpleProxy(sys.stdin),"inputoutput.stdin")        # remote stdin
stdout_uri=d.register(SimpleProxy(sys.stdout),"inputoutput.stdout")     # remote stdout
uri=d.register(RemoteIOManager(stdin_uri, stdout_uri),"example.inputoutput.manager")
print("object uri=",uri)
print("server running.")
d.requestLoop()
