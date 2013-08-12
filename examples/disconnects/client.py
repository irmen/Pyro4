from __future__ import print_function
import sys
import Pyro4
from Pyro4.core import MessageFactory

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
    """

    def _pyroInvoke(self, methodname, vargs, kwargs, flags=0):
        if self._pyroConnection:
            try:
                print("  <proxy: ping>")
                # send the special 'ping' message to the daemon, expecting a 'ping' response (no-op)
                data = MessageFactory.createMessage(MessageFactory.MSG_PING, None, 0, 0)
                self._pyroConnection.send(data)
                MessageFactory.getMessage(self._pyroConnection, [MessageFactory.MSG_PING])
                print("  <proxy: ping reply (still connected)>")
            except Pyro4.errors.ConnectionClosedError:     # or possibly even ProtocolError
                print("  <proxy: Connection lost. REBINDING...>")
                self._pyroReconnect()
                print("  <proxy: Connection restored, continue with actual method call...>")
        return super(AutoReconnectingProxy, self)._pyroInvoke(methodname, vargs, kwargs, flags)


with AutoReconnectingProxy(uri) as obj:
    result = obj.echo("12345")
    print("result =", result)
    print("\nClient proxy connection is still open. Disable the network now (or wait until the connection timeout on the server expires) and see what the server does.")
    print("Once you see on the server that it got a timeout or a disconnect, enable the network again.")
    input("Press enter to continue:")
    print("\nDoing a new call on the same proxy:")
    result = obj.echo("12345")
    print("result =", result)
