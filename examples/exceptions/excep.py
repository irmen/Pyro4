class MyError(Exception):
	pass

class TestClass(object):
	def div(s, arg1, arg2): return arg1/arg2
	def error(s): raise ValueError('a valueerror! Great!')
	def error2(s): return ValueError('a valueerror! Great!')
	def othererr(s): raise MyError('my error!')
	def othererr2(s): return MyError('my error!')
	def complexerror(s):
		x=Foo()
		x.crash()


class Foo(object):
	def crash(s):
		s.crash2('going down...')
	def crash2(s, arg):
		# this statement will crash on purpose:
		x=arg//2
