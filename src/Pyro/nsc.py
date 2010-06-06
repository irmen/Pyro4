"""
Name server control tool.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong.
irmen@razorvine.net - http://www.razorvine.net/python/Pyro
"""

import Pyro.naming
import Pyro.errors

def handleCommand(nameserver, options, args):
    def printListResult(resultdict, title=""):
        print "--------START LIST",title
        for name,uri in sorted(resultdict.items()):
            print "%s --> %s" % (name, uri)
        print "--------END LIST",title
    def cmd_ping():
        nameserver.ping()
        print "Name server ping ok."
    def cmd_listprefix():
        if len(args)==1:
            printListResult(nameserver.list())
        else:
            printListResult(nameserver.list(prefix=args[1]), "- prefix '%s'" % args[1])
    def cmd_listregex():
        if len(args)<2:
            raise SystemExit("missing regex argument")
        printListResult(nameserver.list(regex=args[1]), "- regex '%s'" % args[1])
    def cmd_register():
        nameserver.register(args[1], args[2])
        print "Registered",args[1]
    def cmd_remove():
        count=nameserver.remove(args[1])
        if count>0:
            print "Removed",args[1]
        else:
            print "Nothing removed"
    def cmd_removeregex():
        if len(args)<2:
            raise SystemExit("missing regex argument")
        sure=raw_input("Potentially removing lots of items from the Name server. Are you sure (y/n)?")
        if sure in ('y','Y'):
            count=nameserver.remove(regex=args[1])
            print count,"items removed."

    commands={
        "ping": cmd_ping,
        "list": cmd_listprefix,
        "listmatching": cmd_listregex,
        "register": cmd_register,
        "remove": cmd_remove,
        "removematching": cmd_removeregex        
    }
    try:
        commands[args[0]]()
    except Exception,x:
        print "Error:",x
    
def main(args):
    from optparse import OptionParser
    usage = "usage: %prog [options] command [arguments]\nCommand is one of: " \
            "register remove removematching list listmatching ping"
    parser = OptionParser(usage=usage)
    parser.add_option("-n","--host", dest="host", help="hostname of the NS")
    parser.add_option("-p","--port", dest="port", type="int", 
                      help="port of the NS (or bc-port if host isn't specified)")
    parser.add_option("-v","--verbose", action="store_true", dest="verbose", help="verbose output")
    options,args = parser.parse_args(args)    
    if not args or args[0] not in ("register","remove","removematching","list", "listmatching", "ping"):
        parser.error("invalid or missing command")
    if options.verbose:
        print "Locating name server..."
    try:
        nameserver=Pyro.naming.locateNS(options.host,options.port)
    except Pyro.errors.PyroError,x:
        print "Failed to locate the name server:",x
        return
    if options.verbose:
        print "Name server found:",nameserver._pyroUri
    handleCommand(nameserver, options, args)
    if options.verbose:
        print "Done."

if __name__=="__main__":
    import sys
    main(sys.argv[1:])
