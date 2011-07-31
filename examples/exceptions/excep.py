class MyError(Exception):
    pass

class TestClass(object):
    def div(self, arg1, arg2):
        return arg1/arg2
    def error(self):
        raise ValueError('a valueerror! Great!')
    def error2(self):
        return ValueError('a valueerror! Great!')
    def othererr(self):
        raise MyError('my error!')
    def othererr2(self):
        return MyError('my error!')
    def complexerror(self):
        x=Foo()
        x.crash()


class Foo(object):
    def crash(self):
        self.crash2('going down...')
    def crash2(self, arg):
        # this statement will crash on purpose:
        x=arg//2
