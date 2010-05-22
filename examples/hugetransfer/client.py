#!/usr/bin/env python
import sys, os, time
import Pyro

Pyro.config.COMMTIMEOUT=2

basesize = 500000
data='A'*basesize
totalsize=0

obj=Pyro.core.Proxy("PYRONAME:example.hugetransfer")
print "binding"
obj._pyroBind()
print "done"

begin=time.time()
for i in range(1,15):
    print 'transferring',basesize*i,'bytes'
    size=obj.transfer(data*i)
    # print " reply=",size
    totalsize=totalsize+basesize*i
duration=time.time()-begin

totalsize=float(totalsize)
print 'It took',duration,'seconds to transfer',totalsize/1024,'kilobyte.'
print 'That is',totalsize/1024/duration,'k/sec. = ',totalsize/1024/1024/duration,'mb/sec.'

