import Pyro4


@Pyro4.expose
class bench(object):
    def length(self, string):
        return len(string)

    def timestwo(self, value):
        return value * 2

    def bigreply(self):
        return 'BIG REPLY' * 500

    def bigarg(self, arg):
        return len(arg)

    def manyargs(self, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15):
        return a1 + a2 + a3 + a4 + a5 + a6 + a7 + a8 + a9 + a10 + a11 + a12 + a13 + a14 + a15

    def noreply(self, arg):
        pass

    def varargs(self, *args):
        return len(args)

    def keywords(self, **args):
        return args

    def echo(self, *args):
        return args

    @Pyro4.oneway
    def oneway(self, *args):
        # oneway doesn't return anything
        pass
