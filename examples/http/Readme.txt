A few client programs that demonstrate the use of Pyro's http gateway.
Make sure you first start the gateway, for instance:

    python -m Pyro4.utils.httpgateway    (or just: pyro4-httpgateway)

The code assumes the gateway runs on the default location.

client.js:  javascript client code, for node.js
client.py:  python (3.x) client code

Javascript client code that runs in a browser is problematic due to the same origin policy.
The gateway's web page does contain some examples of this that you can run in your browser.
Simply navigate to the url that is printed when you start the http gateway server.
