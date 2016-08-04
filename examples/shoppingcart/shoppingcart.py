from __future__ import print_function
import Pyro4


@Pyro4.expose
class ShoppingCart(object):
    def __init__(self):
        self.contents = []
        print("(shoppingcart %d taken)" % id(self))

    def purchase(self, item):
        self.contents.append(item)
        print("(%s put into shoppingcart %d)" % (item, id(self)))

    def empty(self):
        self.contents = []

    def getContents(self):
        return self.contents
