"""
Pyro FLAME:  Foreign Location Automatic Module Exposer.
Easy but potentially very dangerous way of exposing remote modules and builtins.
This is the commandline server.

You can start this module as a script from the command line, to easily get a
flame server running:

  :command:`python -m Pyro4.utils.flameserver`
  or simply: :command:`pyro4-flameserver`

You have to explicitly enable Flame first though by setting the FLAME_ENABLED config item.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import print_function
import sys
import os
import warnings
from Pyro4.configuration import config
from Pyro4 import core
from Pyro4.utils import flame


def main(args=None, returnWithoutLooping=False):
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-H", "--host", default="localhost", help="hostname to bind server on (default=%default)")
    parser.add_option("-p", "--port", type="int", default=0, help="port to bind server on")
    parser.add_option("-u", "--unixsocket", help="Unix domain socket name to bind server on")
    parser.add_option("-q", "--quiet", action="store_true", default=False, help="don't output anything")
    parser.add_option("-k", "--key", help="the HMAC key to use (deprecated)")
    options, args = parser.parse_args(args)

    if options.key:
        warnings.warn("using -k to supply HMAC key on the command line is a security problem "
                      "and is deprecated since Pyro 4.72. See the documentation for an alternative.")

    if "PYRO_HMAC_KEY" in os.environ:
        if options.key:
            raise SystemExit("error: don't use -k and PYRO_HMAC_KEY at the same time")
        options.key = os.environ["PYRO_HMAC_KEY"]

    if not options.quiet:
        print("Starting Pyro Flame server.")

    hmac = (options.key or "").encode("utf-8")
    if not hmac and not options.quiet:
        print("Warning: HMAC key not set. Anyone can connect to this server!")

    config.SERIALIZERS_ACCEPTED = {"pickle"}  # flame requires pickle serializer, doesn't work with the others.

    daemon = core.Daemon(host=options.host, port=options.port, unixsocket=options.unixsocket)
    if hmac:
        daemon._pyroHmacKey = hmac
    uri = flame.start(daemon)
    if not options.quiet:
        print("server uri: %s" % uri)
        print("server is running.")

    if returnWithoutLooping:
        return daemon, uri  # for unit testing
    else:
        daemon.requestLoop()
    daemon.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
