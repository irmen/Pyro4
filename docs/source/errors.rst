****************************
Errors and remote tracebacks
****************************

There is an example that shows various ways to deal with exceptions when writing Pyro code.
Have a look at the ``exceptions`` example in the :file:`examples` directory.

Pyro errors
-----------

Pyro's exception classes can be found in :mod:`Pyro4.errors`.
They are used by Pyro if something went wrong inside Pyro itself or related to something Pyro was doing.

Remote errors
-------------
More interesting are the errors that occur in *your own* objects (the remote Pyro objects).
Pyro is doing its best to make the remote objects appear as normal, local, Python objects.
That also means that if they raise an error, Pyro will make it appear in the caller,
as if the error occurred locally.

Say you have a remote object that can divide arbitrary numbers.
It will probably raise a ``ZeroDivisionError`` when you supply ``0`` as the divisor.
This can be dealt with as follows::

    import Pyro4

    divider=Pyro4.Proxy( ... )
    try:
        result = divider.div(999,0)
    except ZeroDivisionError:
        print "yup, it crashed"

Just catch the exception as if you were writing code that deals with normal objects.

But, since the error occurred in a *remote* object, and Pyro itself raises it again on the client
side, you lose some information: the actual traceback of the error at the time it occurred in the server.
Pyro fixes this because it stores the traceback information on a special attribute on the exception
object (``_pyroTraceback``). The traceback is stored as a list of strings (each is a line from
the traceback text, including newlines). You can use this data on the client to print or process the
traceback text from the exception as it occurred in the Pyro object on the server.

There is a utility function in :mod:`Pyro4.util` to make it easy to deal with this:
:func:`Pyro4.util.getPyroTraceback`

You use it like this::

    import Pyro4.util
    try:
        result = proxy.method()
    except Exception:
        print "Pyro traceback:"
        print "".join(Pyro4.util.getPyroTraceback())

Also, there is another function that you can install in ``sys.excepthook``, if you want Python
to automatically print the complete Pyro traceback including the remote traceback, if any:
:func:`Pyro4.util.excepthook`

A full Pyro exception traceback, including the remote traceback on the server, looks something like this::

    Traceback (most recent call last):
      File "client.py", line 50, in <module>
        print(test.complexerror())     # due to the excepthook, the exception will show the pyro error
      File "E:\Projects\Pyro4\src\Pyro4\core.py", line 130, in __call__
        return self.__send(self.__name, args, kwargs)
      File "E:\Projects\Pyro4\src\Pyro4\core.py", line 242, in _pyroInvoke
        raise data
    TypeError: unsupported operand type(s) for //: 'str' and 'int'
     +--- This exception occured remotely (Pyro) - Remote traceback:
     | Traceback (most recent call last):
     |   File "E:\Projects\Pyro4\src\Pyro4\core.py", line 760, in handleRequest
     |     data=method(*vargs, **kwargs)   # this is the actual method call to the Pyro object
     |   File "E:\projects\Pyro4\examples\exceptions\excep.py", line 17, in complexerror
     |     x.crash()
     |   File "E:\projects\Pyro4\examples\exceptions\excep.py", line 22, in crash
     |     s.crash2('going down...')
     |   File "E:\projects\Pyro4\examples\exceptions\excep.py", line 25, in crash2
     |     x=arg//2
     | TypeError: unsupported operand type(s) for //: 'str' and 'int'
     +--- End of remote traceback


As you can see, the first part is only the exception as it occurs locally on the client (raised
by Pyro). The indented part marked with 'Remote traceback' is the exception as it occurred
in the remote Pyro object.

Detailed traceback information
------------------------------

There is another utility that Pyro has to make it easier to debug remote object errors.
If you enable the ``DETAILED_TRACEBACK`` config item on the server (see :ref:`config-items`), the remote
traceback is extended with details of the values of the local variables in every frame::

    +--- This exception occured remotely (Pyro) - Remote traceback:
    | ----------------------------------------------------
    |  EXCEPTION <type 'exceptions.TypeError'>: unsupported operand type(s) for //: 'str' and 'int'
    |  Extended stacktrace follows (most recent call last)
    | ----------------------------------------------------
    | File "E:\Projects\Pyro4\src\Pyro4\core.py", line 760, in Daemon.handleRequest
    | Source code:
    |     data=method(*vargs, **kwargs)   # this is the actual method call to the Pyro object
    | ----------------------------------------------------
    | File "E:\projects\Pyro4\examples\exceptions\excep.py", line 17, in TestClass.complexerror
    | Source code:
    |     x.crash()
    | Local values:
    |     self = <excep.TestClass object at 0x02392830>
    |         self._pyroDaemon = <Pyro4.core.Daemon object at 0x02392330>
    |         self._pyroId = 'obj_c63d47dd140f44dca8782151643e0c55'
    |     x = <excep.Foo object at 0x023929D0>
    | ----------------------------------------------------
    | File "E:\projects\Pyro4\examples\exceptions\excep.py", line 22, in Foo.crash
    | Source code:
    |     self.crash2('going down...')
    | Local values:
    |     self = <excep.Foo object at 0x023929D0>
    | ----------------------------------------------------
    | File "E:\projects\Pyro4\examples\exceptions\excep.py", line 25, in Foo.crash2
    | Source code:
    |     x=arg//2
    | Local values:
    |     arg = 'going down...'
    |     self = <excep.Foo object at 0x023929D0>
    | ----------------------------------------------------
    |  EXCEPTION <type 'exceptions.TypeError'>: unsupported operand type(s) for //: 'str' and 'int'
    | ----------------------------------------------------
    +--- End of remote traceback

You can immediately see why the call produced a ``TypeError`` without the need to have a debugger running
(the ``arg`` variable is a string and dividing that string by 2 ofcourse is the cause of the error).

Ofcourse it is also possible to enable ``DETAILED_TRACEBACK`` on the client, but it is not as useful there
(normally it is no problem to run the client code inside a debugger).
