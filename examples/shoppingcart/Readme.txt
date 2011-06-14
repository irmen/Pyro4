A very simple example that shows the creation and manipulation of
new objects in the server.

It is a shop where the clients need to take a shopping cart
(created in the shop server) and put items in it from the shop's
inventory. After that they take it to the shop's counter to pay
and get a receipt. Due to Pyro's autoproxy feature the shopping carts
are automatically returned to the client as a proxy.

The Shoppingcart objects remain in the shop server. The client code
interacts with them (and with the shop) remotely.
The shop returns a receipt (just a text list of purchased goods) at
checkout time, and puts back the shopping cart (unregisters and deletes
the object) when the client leaves the store.

