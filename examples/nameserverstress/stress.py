#!/usr/bin/env python

import random, time
from threading import Thread
import Pyro

def randomname():
    def partname():
        return str(random.random())[-2:]
    parts=["stresstest"]
    for i in range(random.randint(1,10)):
        parts.append(partname())
    return ".".join(parts)
    

class NamingTrasher(Thread):
    def __init__(self,nsuri,number):
        Thread.__init__(self)
        self.daemon=True
        self.number=number
        self.ns=Pyro.core.Proxy(nsuri)
        self.mustStop=False

    def list(self):
        items=self.ns.list()
    def register(self):
        for i in range(4):
            try:
                self.ns.register(randomname(),'PYRO:objname@host:555')
            except Pyro.errors.NamingError:
                pass
    def remove(self):
        self.ns.remove(randomname())
    def lookup(self):
        try:
            uri=self.ns.lookup(randomname())
        except Pyro.errors.NamingError:
            pass
    def listprefix(self):
        entries=self.ns.list(prefix="stresstest.51")
    def listregex(self):
        entries=self.ns.list(regex=r"stresstest\.??\.41.*")
    def run(self):  
        print 'Name Server trasher running.'
        while not self.mustStop:
            random.choice((self.list, self.register, self.remove, self.lookup, self.listregex, self.listprefix)) ()
            print self.number,
            time.sleep(0.01)
        print 'Trasher exiting.'    

def main():
    threads=[]
    ns=Pyro.naming.locateNS()
    ns.remove(prefix="stresstest.")
    for i in range(5):
        nt=NamingTrasher(ns._pyroUri,i)
        nt.start()
        threads.append(nt)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    print 'Break-- waiting for threads to stop.'
    for nt in threads:
        nt.mustStop=True
        nt.join()
    count=ns.remove(prefix="stresstest.")
    print "cleaned up",count,"names."

if __name__=='__main__':
    main()
