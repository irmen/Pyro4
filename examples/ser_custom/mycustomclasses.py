# defines custom classes


class Thingy(object):
    def __init__(self, num):
        self.number = num

    def __str__(self):
        return "<Thingy @" + hex(id(self)) + ", number=" + str(self.number) + ">"


class OtherThingy(object):
    def __init__(self, num):
        self.number = num

    def __str__(self):
        return "<OtherThingy @" + hex(id(self)) + ", number=" + str(self.number) + ">"
