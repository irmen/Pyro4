from __future__ import print_function
import sys
import random
import time
import threading
import Pyro4.errors
import Pyro4.naming


def randomname():
    def partname():
        return str(random.random())[-2:]

    parts = ["stresstest"]
    for i in range(random.randint(1, 10)):
        parts.append(partname())
    return ".".join(parts)


class NamingTrasher(threading.Thread):
    def __init__(self, nsuri, number):
        threading.Thread.__init__(self)
        self.daemon = True
        self.number = number
        self.ns = Pyro4.core.Proxy(nsuri)
        self.mustStop = False

    def list(self):
        items = self.ns.list()

    def register(self):
        for i in range(4):
            try:
                self.ns.register(randomname(), 'PYRO:objname@host:555')
            except Pyro4.errors.NamingError:
                pass

    def remove(self):
        self.ns.remove(randomname())

    def lookup(self):
        try:
            uri = self.ns.lookup(randomname())
        except Pyro4.errors.NamingError:
            pass

    def listprefix(self):
        entries = self.ns.list(prefix="stresstest.51")

    def listregex(self):
        entries = self.ns.list(regex=r"stresstest\.??\.41.*")

    def run(self):
        print("Name Server trasher running.")
        while not self.mustStop:
            random.choice((self.list, self.register, self.remove, self.lookup, self.listregex, self.listprefix))()
            sys.stdout.write("%d " % self.number)
            sys.stdout.flush()
            time.sleep(0.001)
        print("Trasher exiting.")


def main():
    threads = []
    ns = Pyro4.naming.locateNS()
    print("Removing previous stresstest registrations...")
    ns.remove(prefix="stresstest.")
    print("Done. Starting.")
    for i in range(5):
        nt = NamingTrasher(ns._pyroUri, i)
        nt.start()
        threads.append(nt)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    print("Break-- waiting for threads to stop.")
    for nt in threads:
        nt.mustStop = True
        nt.join()
    count = ns.remove(prefix="stresstest.")
    print("cleaned up %d names." % count)


if __name__ == '__main__':
    main()
