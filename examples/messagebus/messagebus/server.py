"""
Pyro MessageBus:  a simple pub/sub message bus.
Provides a way of cummunicating where the sender and receivers are fully decoupled.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import print_function
import sys
from . import PYRO_MSGBUS_NAME
from .messagebus import make_messagebus, MessageBus
import Pyro4


Pyro4.config.COMMTIMEOUT = 20.0
Pyro4.config.POLLTIMEOUT = 10.0
Pyro4.config.MAX_MESSAGE_SIZE = 256*1024     # 256 kb
Pyro4.config.MAX_RETRIES = 3


if __name__ == "__main__":
    # @todo use optparse
    if len(sys.argv) != 3:
        raise SystemExit("provide hostname to bind on, and storage type (sqlite/memory) as arguments")
    hostname = sys.argv[1].strip()
    if sys.argv[2] not in ("sqlite", "memory"):
        raise ValueError("invalid storagetype")
    make_messagebus.storagetype = sys.argv[2]
    Pyro4.Daemon.serveSimple({MessageBus: PYRO_MSGBUS_NAME}, host=hostname)
