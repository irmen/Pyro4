# this is the program whose input/output you can redirect
from __future__ import print_function
import sys
import Pyro4

if sys.version_info<(3,0):
    input=raw_input

sys.excepthook=Pyro4.util.excepthook


def interaction():
    print("Hello there.")
    name=input("What is your name? ").strip()
    year=input("What year were you born? ").strip()
    print("Nice meeting you, {0}!".format(name))
    print("I heard the wine from {0} was particularly good.".format(year))



def main():
    uri=input("uri of the remote i/o server, or enter for local i/o:").strip()
    print(repr(uri))
    if uri:
        try:
            remoteIO = Pyro4.Proxy(uri)
            remote_stdout, remote_stdin = remoteIO.getInputOutput()
            print("Replacing sys.stdin and sys.stdout. Read and type on the server :-)")
            orig_stdin=sys.stdin
            orig_stdout=sys.stdout
            sys.stdin=remote_stdin   # just put a proxy in place of stdin/stdout...
            sys.stdout=remote_stdout  # ... all i/o calls will be passed to the remote object
            print("---remote interaction starts---")
            interaction()    # call the interaction loop
            print("---remote interaction ends---")
        finally:
            sys.stdout=orig_stdout
            sys.stdin=orig_stdin
    else:
        print("just running locally")
        interaction()

if __name__=="__main__":
    main()
  