from __future__ import print_function
import Pyro4
import Pyro4.socketutil
import bench

Pyro4.Daemon.serveSimple({
        bench.bench: "example.benchmark"
    },
    daemon=Pyro4.Daemon(host=Pyro4.socketutil.getIpAddress("")),
    ns=False)
