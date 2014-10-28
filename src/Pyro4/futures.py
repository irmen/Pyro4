"""
Support for Futures (asynchronously executed callables).
If you're using Python 3.2 or newer, also see
http://docs.python.org/3/library/concurrent.futures.html#future-objects

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import sys
import functools
import logging
import Pyro4.util
from Pyro4 import threadutil


__all__ = ["Future", "FutureResult", "_ExceptionWrapper"]

log = logging.getLogger("Pyro4.futures")


class Future(object):
    """
    Holds a callable that will be executed asynchronously and provide its
    result value some time in the future.
    This is a more general implementation than the AsyncRemoteMethod, which
    only works with Pyro proxies (and provides a bit different syntax).
    """

    def __init__(self, somecallable):
        self.callable = somecallable
        self.chain = []
        self.exceptionhandler = None

    def __call__(self, *args, **kwargs):
        """
        Start the future call with the provided arguments.
        Control flow returns immediately, with a FutureResult object.
        """
        chain = self.chain
        del self.chain  # make it impossible to add new calls to the chain once we started executing it
        result = FutureResult()  # notice that the call chain doesn't sit on the result object
        thread = threadutil.Thread(target=self.__asynccall, args=(result, chain, args, kwargs))
        thread.setDaemon(True)
        thread.start()
        return result

    def __asynccall(self, asyncresult, chain, args, kwargs):
        try:
            value = self.callable(*args, **kwargs)
            # now walk the callchain, passing on the previous value as first argument
            for call, args, kwargs in chain:
                call = functools.partial(call, value)
                value = call(*args, **kwargs)
            asyncresult.value = value
        except Exception as x:
            if self.exceptionhandler:
                self.exceptionhandler(x)
            asyncresult.value = _ExceptionWrapper(sys.exc_info()[1])

    def then(self, call, *args, **kwargs):
        """
        Add a callable to the call chain, to be invoked when the results become available.
        The result of the current call will be used as the first argument for the next call.
        Optional extra arguments can be provided in args and kwargs.
        Returns self so you can easily chain then() calls.
        """
        self.chain.append((call, args, kwargs))
        return self

    def iferror(self, exceptionhandler):
        """
        Specify the exception handler to be invoked (with the exception object as only
        argument) when calculating the result raises an exception.
        If no exception handler is set, any exception raised in the async call will be silently ignored.
        Returns self so you can easily chain other calls.
        """
        self.exceptionhandler = exceptionhandler
        return self


class FutureResult(object):
    """
    The result object for asynchronous calls.
    """

    def __init__(self):
        self.__ready = threadutil.Event()
        self.callchain = []
        self.valueLock = threadutil.Lock()
        self.exceptionhandler = None

    def wait(self, timeout=None):
        """
        Wait for the result to become available, with optional timeout (in seconds).
        Returns True if the result is ready, or False if it still isn't ready.
        """
        result = self.__ready.wait(timeout)
        if result is None:
            # older pythons return None from wait()
            return self.__ready.isSet()
        return result

    @property
    def ready(self):
        """Boolean that contains the readiness of the async result"""
        return self.__ready.isSet()

    def get_value(self):
        self.__ready.wait()
        if isinstance(self.__value, _ExceptionWrapper):
            self.__value.raiseIt()
        else:
            return self.__value

    def set_value(self, value):
        with self.valueLock:
            self.__value = value
            # walk the call chain if the result is not an exception, otherwise invoke the errorhandler (if any)
            if isinstance(value, _ExceptionWrapper):
                if self.exceptionhandler:
                    self.exceptionhandler(value.exception)
            else:
                for call, args, kwargs in self.callchain:
                    call = functools.partial(call, self.__value)
                    self.__value = call(*args, **kwargs)
                    if isinstance(self.__value, _ExceptionWrapper):
                        break
            self.callchain = []
            self.__ready.set()

    value = property(get_value, set_value, None, "The result value of the call. Reading it will block if not available yet.")

    def then(self, call, *args, **kwargs):
        """
        Add a callable to the call chain, to be invoked when the results become available.
        The result of the current call will be used as the first argument for the next call.
        Optional extra arguments can be provided in args and kwargs.
        Returns self so you can easily chain then() calls.
        """
        with self.valueLock:
            if self.__ready.isSet():
                # value is already known, we need to process it immediately (can't use the call chain anymore)
                call = functools.partial(call, self.__value)
                self.__value = call(*args, **kwargs)
            else:
                # add the call to the call chain, it will be processed later when the result arrives
                self.callchain.append((call, args, kwargs))
            return self

    def iferror(self, exceptionhandler):
        """
        Specify the exception handler to be invoked (with the exception object as only
        argument) when asking for the result raises an exception.
        If no exception handler is set, any exception result will be silently ignored (unless
        you explicitly ask for the value). Returns self so you can easily chain other calls.
        """
        self.exceptionhandler = exceptionhandler
        return self


class _ExceptionWrapper(object):
    """Class that wraps a remote exception. If this is returned, Pyro will
    re-throw the exception on the receiving side. Usually this is taken care of
    by a special response message flag, but in the case of batched calls this
    flag is useless and another mechanism was needed."""

    def __init__(self, exception):
        self.exception = exception

    def raiseIt(self):
        if sys.platform == "cli":
            Pyro4.util.fixIronPythonExceptionForPickle(self.exception, False)
        raise self.exception

    def __serialized_dict__(self):
        """serialized form as a dictionary"""
        return {
            "__class__": "Pyro4.futures._ExceptionWrapper",
            "exception": Pyro4.util.SerializerBase.class_to_dict(self.exception)
        }
