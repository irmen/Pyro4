This example shows a nifty use of a Pyro proxy object.
We use it to replace sys.stdin and sys.stdout, so that all input
and output is handled by a remote program instead.

inputoutput.py is the i/o 'server' that provides the remote input/output
program.py is a simple program that asks a few lines of input from the
user and prints a few lines of resulting text. If you feed it the URI of
the inputoutput server, it will replace the local stdin/stdout with the
appropriate Pyro proxies, so that it now does its i/o remotely.

There's one special thing going on in the inputoutput server:
it needs to wrap the stdin/stdout file objects with a simple proxy object
because otherwise Pyro can't inject its custom attributes that it needs
to be able to treat the object (file stream) as a Pyro object.
The proxy 'knows' that all special Pyro attributes start with _pyro.
Also, it needs to intercept the fileno attribute and pretend it doesn't
exist, otherwise the thing doesn't seem to work on Python 3.x.

