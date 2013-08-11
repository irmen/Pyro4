This is an example that shows the autoproxy feature.
Pyro will automatically return a Proxy instead of the object itself,
if you are passing a Pyro object over a remote call.

This means you can easily create new objects in a server and return them
from remote calls, without the need to manually wrap them in a proxy.

This behavior is enabled by default. It is different from older Pyro releases,
so there is a config item AUTOPROXY that you can set to False if you want
the old behaviour. You can try it with this example too, set the environment
variable PYRO_AUTOPROXY to false and restart the server to see what
the effect is.

Note that when using the marshal serializer, this feature will not work.
