#!/usr/bin/env python
import time
import Pyro
from shoppingcart import ShoppingCart

class Shop(object):
    inventory= {
        "paper"     : 1.25,
        "bread"     : 1.50,
        "meat"      : 5.99,
        "milk"      : 0.80,
        "fruit"     : 2.65,
        "chocolate" : 3.99,
        "pasta"     : 0.50,
        "sauce"     : 1.20,
        "vegetables": 1.40,
        "cookies"   : 1.99,
        "pizza"     : 3.60,
        "shampoo"   : 2.22,
        "whiskey"   : 24.99
        }

    customersInStore={}
    
    def enter(self, name):
        print "Customer %s enters the store." % name
        print "Customer takes a shopping cart."
        # create a cart and return it as a pyro object to the client
        cart=ShoppingCart()
        self.customersInStore[name]=cart
        return self.__proxyfy(cart)
    def customers(self):
        return self.customersInStore.keys()
    def goods(self):
        return self.inventory
    def payByName(self, name):
        print "Customer %s goes to the counter to pay." % name
        cart=self.customersInStore[name]
        return self.payCart(cart, name)
    def payCart(self,cart,name=None):
        receipt=[]
        if name:
            receipt.append("Receipt for %s." % name)
        receipt.append("Receipt Date: "+time.asctime())
        total=0.0
        for item in cart.getContents():
            price=self.inventory[item]
            total+=price
            receipt.append("%13s  %.2f" % (item,price))
        receipt.append("")
        receipt.append("%13s  %.2f" % ("total:",total))
        cart.empty()
        return "\n".join(receipt)
    def leave(self, name):
        print "Customer %s leaves." % name
        cart=self.customersInStore[name]
        print "  their shopping cart contains:",cart.getContents()
        if cart.getContents():
            print "  it is not empty, they are trying to shoplift!"
            raise Exception("attempt to steal a full cart prevented")
        # delete the cart and unregister it with pyro
        del self.customersInStore[name]
        self.__unproxyfy(cart)
    
    # utility methods:
    def __proxyfy(self, object):
        """register the object with the daemon and return a proxy"""
        uri=self._pyroDaemon.register(object)
        return Pyro.Proxy(uri)
    def __unproxyfy(self, object):
        """unregister the object with the daemon"""
        self._pyroDaemon.unregister(object)


######## main program

daemon=Pyro.Daemon()
shop=Shop()
uri=daemon.register(shop)
ns=Pyro.locateNS()
ns.remove("example.shop")
ns.register("example.shop", uri)
print "Shop Server is ready."
daemon.requestLoop()
