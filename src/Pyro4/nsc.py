"""
Name server control tool.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import print_function
import sys
import os
import warnings
from Pyro4 import errors, naming

if sys.version_info < (3, 0):
    input = raw_input


def handleCommand(nameserver, options, args):
    def printListResult(resultdict, title=""):
        print("--------START LIST %s" % title)
        for name, (uri, metadata) in sorted(resultdict.items()):
            print("%s --> %s" % (name, uri))
            if metadata:
                print("    metadata:", metadata)
        print("--------END LIST %s" % title)

    def cmd_ping():
        nameserver.ping()
        print("Name server ping ok.")

    def cmd_listprefix():
        if len(args) == 1:
            printListResult(nameserver.list(return_metadata=True))
        else:
            printListResult(nameserver.list(prefix=args[1], return_metadata=True), "- prefix '%s'" % args[1])

    def cmd_listregex():
        if len(args) != 2:
            raise SystemExit("requires one argument: pattern")
        printListResult(nameserver.list(regex=args[1], return_metadata=True), "- regex '%s'" % args[1])

    def cmd_lookup():
        if len(args) != 2:
            raise SystemExit("requires one argument: name")
        uri, metadata = nameserver.lookup(args[1], return_metadata=True)
        print(uri)
        if metadata:
            print("metadata:", metadata)

    def cmd_register():
        if len(args) != 3:
            raise SystemExit("requires two arguments: name uri")
        nameserver.register(args[1], args[2], safe=True)
        print("Registered %s" % args[1])

    def cmd_remove():
        if len(args) != 2:
            raise SystemExit("requires one argument: name")
        count = nameserver.remove(args[1])
        if count > 0:
            print("Removed %s" % args[1])
        else:
            print("Nothing removed")

    def cmd_removeregex():
        if len(args) != 2:
            raise SystemExit("requires one argument: pattern")
        sure = input("Potentially removing lots of items from the Name server. Are you sure (y/n)?").strip()
        if sure in ('y', 'Y'):
            count = nameserver.remove(regex=args[1])
            print("%d items removed." % count)

    def cmd_setmeta():
        if len(args) < 2:
            raise SystemExit("requires at least 2 arguments: uri and zero or more meta tags")
        metadata = set(args[2:])
        nameserver.set_metadata(args[1], metadata)
        if metadata:
            print("Metadata updated")
        else:
            print("Metadata cleared")

    def cmd_listmeta_all():
        if len(args) < 2:
            raise SystemExit("requires at least one metadata tag argument")
        metadata = set(args[1:])
        printListResult(nameserver.list(metadata_all=metadata, return_metadata=True), " - searched by metadata")

    def cmd_listmeta_any():
        if len(args) < 2:
            raise SystemExit("requires at least one metadata tag argument")
        metadata = set(args[1:])
        printListResult(nameserver.list(metadata_any=metadata, return_metadata=True), " - searched by metadata")

    commands = {
        "ping": cmd_ping,
        "list": cmd_listprefix,
        "listmatching": cmd_listregex,
        "listmeta_all": cmd_listmeta_all,
        "listmeta_any": cmd_listmeta_any,
        "lookup": cmd_lookup,
        "register": cmd_register,
        "remove": cmd_remove,
        "removematching": cmd_removeregex,
        "setmeta": cmd_setmeta
    }
    try:
        commands[args[0]]()
    except Exception as x:
        print("Error: %s - %s" % (type(x).__name__, x))


def main(args=None):
    from optparse import OptionParser
    usage = "usage: %prog [options] command [arguments]\nCommands: " \
            "register remove removematching lookup list listmatching\n          listmeta_all listmeta_any setmeta ping"
    parser = OptionParser(usage=usage)
    parser.add_option("-n", "--host", dest="host", help="hostname of the NS")
    parser.add_option("-p", "--port", dest="port", type="int",
                      help="port of the NS (or bc-port if host isn't specified)")
    parser.add_option("-u", "--unixsocket", help="Unix domain socket name of the NS")
    parser.add_option("-k", "--key", help="the HMAC key to use (deprecated)")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", help="verbose output")
    options, args = parser.parse_args(args)
    if options.key:
        warnings.warn("using -k to supply HMAC key on the command line is a security problem "
                      "and is deprecated since Pyro 4.72. See the documentation for an alternative.")
    if "PYRO_HMAC_KEY" in os.environ:
        if options.key:
            raise SystemExit("error: don't use -k and PYRO_HMAC_KEY at the same time")
        options.key = os.environ["PYRO_HMAC_KEY"]
    if not args or args[0] not in ("register", "remove", "removematching", "list", "listmatching", "lookup",
                                   "listmeta_all", "listmeta_any", "setmeta", "ping"):
        parser.error("invalid or missing command")
    if options.verbose:
        print("Locating name server...")
    if options.unixsocket:
        options.host = "./u:" + options.unixsocket
    try:
        nameserver = naming.locateNS(options.host, options.port, hmac_key=options.key)
    except errors.PyroError as x:
        print("Error: %s" % x)
        return
    if options.verbose:
        print("Name server found: %s" % nameserver._pyroUri)
    handleCommand(nameserver, options, args)
    if options.verbose:
        print("Done.")


if __name__ == "__main__":
    main()
