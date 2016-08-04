from __future__ import print_function
import time

import Pyro4
from shoppingcart import ShoppingCart


@Pyro4.expose
class Shop(object):
    inventory = {
        "paper": 1.25,
        "bread": 1.50,
        "meat": 5.99,
        "milk": 0.80,
        "fruit": 2.65,
        "chocolate": 3.99,
        "pasta": 0.50,
        "sauce": 1.20,
        "vegetables": 1.40,
        "cookies": 1.99,
        "pizza": 3.60,
        "shampoo": 2.22,
        "whiskey": 24.99
    }

    customersInStore = {}

    def enter(self, name):
        print("Customer %s enters the store." % name)
        print("Customer takes a shopping cart.")
        # create a cart and return it as a pyro object to the client
        cart = ShoppingCart()
        self.customersInStore[name] = cart
        self._pyroDaemon.register(cart)  # make cart a pyro object
        return cart

    def customers(self):
        return list(self.customersInStore.keys())

    def goods(self):
        return self.inventory

    def payByName(self, name):
        print("Customer %s goes to the counter to pay." % name)
        cart = self.customersInStore[name]
        return self.payCart(cart, name)

    def payCart(self, cart, name=None):
        receipt = []
        if name:
            receipt.append("Receipt for %s." % name)
        receipt.append("Receipt Date: " + time.asctime())
        total = 0.0
        for item in cart.getContents():
            price = self.inventory[item]
            total += price
            receipt.append("%13s  %.2f" % (item, price))
        receipt.append("")
        receipt.append("%13s  %.2f" % ("total:", total))
        cart.empty()
        return "\n".join(receipt)

    def leave(self, name):
        print("Customer %s leaves." % name)
        cart = self.customersInStore[name]
        print("  their shopping cart contains: %s" % cart.getContents())
        if cart.getContents():
            print("  it is not empty, they are trying to shoplift!")
            raise Exception("attempt to steal a full cart prevented")
        # delete the cart and unregister it with pyro
        del self.customersInStore[name]
        self._pyroDaemon.unregister(cart)


# main program

Pyro4.Daemon.serveSimple({
    Shop: "example.shop"
})
