# this module will be sent to the server as 'flameexample.stuff'

from __future__ import print_function


def doSomething(name, number):
    print("This text is printed from a module whose code was uploaded by the client:")
    print("  Hello, my name is {0} and my number is {1}.".format(name, number))
    return 999
