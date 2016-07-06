# This is an AWESOME LIBRARY.
# You can use its AWESOME CLASSES to do Great Things.
# The author however DOESN'T allow you to CHANGE the source code and taint it with Pyro decorators!


class WeirdReturnType(object):
    def __init__(self, value):
        self.value = value


class AwesomeClass(object):
    def method(self, arg):
        print("Awesome object is called with: ", arg)
        return "awesome"

    def private(self):
        print("This should be a private method...")
        return "boo"

    def weird(self):
        print("Weird!")
        return WeirdReturnType("awesome")
