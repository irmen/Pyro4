"""
Echo server for test purposes.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong.
irmen@razorvine.net - http://www.razorvine.net/projects/Pyro
"""

import sys, os, time
from Pyro4 import threadutil
from Pyro4 import naming
import Pyro4


class EchoServer(object):
    verbose=False
    must_shutdown=False

    def echo(self, args):
        if self.verbose:
            print ("%s - echo: %s" % (time.asctime(), args))
        return args

    def error(self):
        if self.verbose:
            print ("%s - error: generating exception" % time.asctime())
        return 1//0   # division by zero error

    def shutdown(self):
        if self.verbose:
            print ("%s - shutting down" % time.asctime())
        self.must_shutdown=True


class NameServer(threadutil.Thread):
    def __init__(self, hostname):
        super(NameServer,self).__init__()
        self.setDaemon(1)
        self.hostname=hostname
        self.started=threadutil.Event()

    def run(self):
        self.uri, self.ns_daemon, self.bc_server = naming.startNS(self.hostname)
        self.started.set()
        self.ns_daemon.requestLoop()


def startNameServer(host):
    ns=NameServer(host)
    ns.start()
    ns.started.wait()
    return ns


def main(args, returnWithoutLooping=False):
    from optparse import OptionParser
    parser=OptionParser()
    parser.add_option("-H","--host", default="localhost", help="hostname to bind server on (default=localhost)")
    parser.add_option("-p","--port", type="int", default=0, help="port to bind server on")
    parser.add_option("-n","--naming", action="store_true", default=False, help="register with nameserver")
    parser.add_option("-N","--nameserver", action="store_true", default=False, help="also start a nameserver")
    parser.add_option("-v","--verbose", action="store_true", default=False, help="verbose output")
    parser.add_option("-q","--quiet", action="store_true", default=False, help="don't output anything")
    options,args = parser.parse_args(args)

    if options.verbose:
        options.quiet=False
    if not options.quiet:
        print ("Starting Pyro's built-in test echo server.")
    if os.name!="java":
        Pyro4.config.SERVERTYPE="multiplex"

    if not Pyro4.config.HMAC_KEY:
        if sys.version_info<(3,0):
            Pyro4.config.HMAC_KEY="testkey"
        else:
            Pyro4.config.HMAC_KEY=bytes("testkey","utf-8")
        if not options.quiet:
            print("HMAC_KEY set to built-in default: %s" % Pyro4.config.HMAC_KEY)

    nameserver=None
    if options.nameserver:
        options.naming=True
        nameserver=startNameServer(options.host)

    d=Pyro4.Daemon(host=options.host, port=options.port)
    echo=EchoServer()
    echo.verbose=options.verbose
    objectName="test.echoserver"
    uri=d.register(echo, objectName)
    if options.naming:
        host,port=None,None
        if nameserver is not None:
            host,port=nameserver.uri.host, nameserver.uri.port
        ns=naming.locateNS(host,port)
        ns.remove(objectName)
        ns.register(objectName, uri)
        if options.verbose:
            print ("using name server at %s" % ns._pyroUri)
    else:
        if options.verbose:
            print ("not using a name server.")
    if not options.quiet:
        print ("object name: %s" % objectName)
        print ("echo uri: %s" % uri)
        print ("echoserver running.")

    if returnWithoutLooping:
        return d,echo,uri        # for unit testing
    else:
        d.requestLoop(loopCondition=lambda:not echo.must_shutdown)
    d.close()

if __name__=="__main__":
    main(sys.argv[1:])
