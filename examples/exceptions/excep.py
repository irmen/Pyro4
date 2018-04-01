import pickle
import Pyro4


class UnserializableError(Exception):
    def __reduce__(self):
        raise pickle.PicklingError("make this nonpickleable")


@Pyro4.expose
class TestClass(object):
    def div(self, arg1, arg2):
        return arg1 / arg2

    def error(self):
        raise ValueError('a valueerror! Great!')

    def error2(self):
        return ValueError('a valueerror! Great!')

    def othererr(self):
        raise RuntimeError('a runtime error!')

    def complexerror(self):
        x = Foo()
        x.crash()

    def unserializable(self):
        raise UnserializableError("this error can't be serialized")


class Foo(object):
    def crash(self):
        self.crash2('going down...')

    def crash2(self, arg):
        # this statement will crash on purpose:
        x = arg // 2
