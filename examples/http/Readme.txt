A few client programs that demonstrate the use of Pyro's http gateway.
Make sure you first start the gateway, for instance:

    python -m Pyro4.utils.httpgateway -e 'Pyro.|test.'
    or: pyro4-httpgateway -e 'Pyro.|test.'


The code assumes the gateway runs on the default location.
The '-e' option tells it to expose all Pyro objects (such as the name server) and
the test objects (such as the test echo server).

For completeness, also start the test echoserver (pyro4-test-echoserver)
Then run a client of your choosing:

client.js:  javascript client code, for node.js
client.py:  python (3.x) client code
... and try opening the url that the server printed in your web browser.


Javascript client code that runs in a browser is problematic due to the same origin policy.
The gateway's web page does contain some examples of this that you can run in your browser.
Simply navigate to the url that is printed when you start the http gateway server.
