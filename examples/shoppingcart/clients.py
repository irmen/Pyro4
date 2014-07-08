from __future__ import print_function
import random

import Pyro4


shop = Pyro4.Proxy("PYRONAME:example.shop")

print("Simulating some customers.")
harrysCart = shop.enter("Harry")
sallysCart = shop.enter("Sally")
shoplifterCart = shop.enter("shoplifter")
# harry buys 4 things and sally 5, shoplifter takes 3 items
# note that we put the item directly in the shopping cart.
goods = list(shop.goods().keys())
for i in range(4):
    item = random.choice(goods)
    print("Harry buys %s" % item)
    harrysCart.purchase(item)
for i in range(5):
    item = random.choice(goods)
    print("Sally buys %s" % item)
    sallysCart.purchase(item)
for i in range(3):
    item = random.choice(goods)
    print("Shoplifter takes %s" % item)
    shoplifterCart.purchase(item)

print("Customers currently in the shop: %s" % shop.customers())

# Go to the counter to pay and get a receipt.
# The shopping cart is still 'inside the shop' (=on the server)
# so it knows what is in there for every customer in the store.
# Harry pays by just telling his name (and the shop  looks up
# harry's shoppingcart).
# Sally just hands in her shopping cart directly.
# The shoplifter tries to leave without paying.

try:
    receipt = shop.payByName("Harry")
except:
    print("ERROR: %s" % ("".join(Pyro4.util.getPyroTraceback())))
print("Harry payed. The cart now contains: %s (should be empty)" % harrysCart.getContents())
print("Harry got this receipt:")
print(receipt)
receipt = shop.payCart(sallysCart)
print("Sally payed. The cart now contains: %s (should be empty)" % sallysCart.getContents())
print("Sally got this receipt:")
print(receipt)
print("Harry is leaving.")
shop.leave("Harry")
print("Sally is leaving.")
shop.leave("Sally")
print("Shoplifter is leaving. (should be impossible i.e. give an error)")
try:
    shop.leave("shoplifter")
except:
    print("".join(Pyro4.util.getPyroTraceback()))

print("Harry is attempting to put stuff back in his cart again,")
print("which should fail because the cart does no longer exist.")
harrysCart.purchase("crap")
