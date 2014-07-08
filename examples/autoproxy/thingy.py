class Thingy(object):
    def __init__(self, number):
        self.number = number

    def speak(self, message):
        print("Thingy {0} says: {1}".format(self.number, message))
