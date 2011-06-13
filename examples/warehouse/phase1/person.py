from __future__ import print_function
import sys

if sys.version_info<(3,0):
    input=raw_input


class Person(object):
    def __init__(self, name):
        self.name=name
    def visit(self, warehouse):
        print("This is {0}.".format(self.name))
        self.deposit(warehouse)
        self.retrieve(warehouse)
        print("Thank you, come again!")
    def deposit(self, warehouse):
        print("The warehouse contains:", warehouse.list_contents())
        item=input("Type a thing you want to store (or empty): ").strip()
        if item:
            warehouse.store(self, item)
    def retrieve(self, warehouse):
        print("The warehouse contains:", warehouse.list_contents())
        item=input("Type something you want to take (or empty): ").strip()
        if item:
            warehouse.take(self, item)
