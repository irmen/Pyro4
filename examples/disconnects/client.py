from __future__ import print_function
import sys
import warnings

import Pyro4
import Pyro4.message


warnings.filterwarnings("ignore")

if sys.version_info < (3, 0):
    input = raw_input

print("You can run this client on a different computer so you can disable the network connection (by yanking out the lan cable or whatever).")
print("Alternatively, wait for a timeout on the server, which will then close its connection.")
uri = input("Uri of server? ").strip()


class AutoReconnectingProxy(Pyro4.core.Proxy):
    """
    A Pyro proxy that automatically recovers from a server disconnect.
    It does this by intercepting every method call and then it first 'pings'
    the server to see if it still has a working connection. If not, it
    reconnects the proxy and retries the method call.
    Drawback is that every method call now uses two remote messages (a ping,
    and the actual method call).
    This uses some advanced features of the Pyro API.
    """

    def _pyroInvoke(self, *args, **kwargs):
        # We override the method that does the actual remote calls: _pyroInvoke.
        # If there's still a connection, try a ping to see if it is still alive.
        # If it isn't alive, reconnect it. If there's no connection, simply call
        # the original method (it will reconnect automatically).
        if self._pyroConnection:
            try:
                print("  <proxy: ping>")
                Pyro4.message.Message.ping(self._pyroConnection, hmac_key=None)    # utility method on the Message class
                print("  <proxy: ping reply (still connected)>")
            except Pyro4.errors.ConnectionClosedError:
                print("  <proxy: Connection lost. REBINDING...>")
                self._pyroReconnect()
                print("  <proxy: Connection restored, continue with actual method call...>")
        return super(AutoReconnectingProxy, self)._pyroInvoke(*args, **kwargs)


with AutoReconnectingProxy(uri) as obj:
    result = obj.echo("12345")
    print("result =", result)
    print("\nClient proxy connection is still open. Disable the network now (or wait until the connection timeout on the server expires) and see what the server does.")
    print("Once you see on the server that it got a timeout or a disconnect, enable the network again.")
    input("Press enter to continue:")
    print("\nDoing a new call on the same proxy:")
    result = obj.echo("12345")
    print("result =", result)
