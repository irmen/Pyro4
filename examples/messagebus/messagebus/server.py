"""
Pyro MessageBus:  a simple pub/sub message bus.
Provides a way of cummunicating where the sender and receivers are fully decoupled.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import print_function
from optparse import OptionParser
from . import PYRO_MSGBUS_NAME
from .messagebus import make_messagebus, MessageBus
import Pyro4


Pyro4.config.COMMTIMEOUT = 20.0
Pyro4.config.POLLTIMEOUT = 10.0
Pyro4.config.MAX_MESSAGE_SIZE = 256*1024     # 256 kb
Pyro4.config.MAX_RETRIES = 3


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-n", "--host", dest="host", default="localhost", help="hostname to bind server on")
    parser.add_option("-p", "--port", dest="port", type="int", default=0, help="port to bind server on (0=random)")
    parser.add_option("-u", "--unixsocket", help="Unix domain socket name to bind server on")
    parser.add_option("-s", "--storage", dest="storage", type="choice", choices=["sqlite", "memory"], default="sqlite", help="storage type (default=%default)")
    options, args = parser.parse_args()
    make_messagebus.storagetype = options.storage
    daemon = Pyro4.Daemon(host=options.host, port=options.port, unixsocket=options.unixsocket)
    uri = daemon.register(MessageBus)
    print("Pyro Message Bus.")
    print("    uri  =", uri)
    ns = Pyro4.locateNS()
    ns.register(PYRO_MSGBUS_NAME, uri)
    print("    name =", PYRO_MSGBUS_NAME)
    print("Server running, storage is {}.".format(make_messagebus.storagetype))
    daemon.requestLoop()
