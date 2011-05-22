class sub1(object):
    def meth1(s,arg):
        return 'This is sub1.meth1'
class sub2(sub1):
    def meth2(s,arg):
        return 'This is sub2.meth2'
class sub3(sub2):
    def meth3(s,arg):
        return 'This is sub3.meth3'
class sub4(sub3,sub2):
    def meth4(s,arg):
        return 'This is sub4.meth4'

class bench(sub4):
    def ping(self):
        pass
    def length(self, string):
        return len(string)
    def timestwo(self, value):
        return value*2
    def bigreply(self):
        return 'BIG REPLY'*500
    def bigarg(self,arg):
        return len(arg)
    def manyargs(self, a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12,a13,a14,a15):
        return a1+a2+a3+a4+a5+a6+a7+a8+a9+a10+a11+a12+a13+a14+a15
    def noreply(self, arg):
        pass
    def varargs(self, *args):
        return len(args)
    def keywords(self, **args):
        return args
    def echo(self, *args):
        return args
    def oneway(self, *args):
        # oneway doesn't return anything
        pass
    def mapping(self, mapping):
        return mapping
