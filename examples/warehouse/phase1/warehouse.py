from __future__ import print_function


class Warehouse(object):
    def __init__(self):
        self.contents=["chair","bike","flashlight","laptop","couch"]

    def list_contents(self):
        return self.contents

    def take(self, person, item):
        self.contents.remove(item)
        print("{0} took the {1}.".format(person.name, item))

    def store(self, person, item):
        self.contents.append(item)
        print("{0} stored the {1}.".format(person.name, item))
