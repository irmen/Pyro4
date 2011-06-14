from __future__ import with_statement
import sys
import time
import Pyro4
from Pyro4 import threadutil

if sys.version_info<(3,0):
    current_thread=threadutil.currentThread
else:
    current_thread=threadutil.current_thread

serv = Pyro4.core.Proxy("PYRONAME:example.servertypes")
serv._pyroOneway.add("onewaydelay")

print("--------------------------------------------------------------")
print("    This part is independent of the type of the server.       ")
print("--------------------------------------------------------------")
print("Calling 5 times oneway method. Should return immediately.")
serv.reset()
begin=time.time()
serv.onewaydelay()
serv.onewaydelay()
serv.onewaydelay()
serv.onewaydelay()
serv.onewaydelay()
print("Done with the oneway calls.")
completed=serv.getcount()
print("Number of completed calls in the server: %d" % completed)
print("This should be 0, because all 5 calls are still busy in the background.")
if completed>0:
    print("  !!! The oneway calls were not running in the background !!!")
    print("  ??? Are you sure ONEWAY_THREADED=True on the server ???")
print()
print("Calling normal delay 5 times. They will all be processed")
print("by the same server thread because we're using the same proxy.")
r=serv.delay()
print("  call processed by: %s" % r)
r=serv.delay()
print("  call processed by: %s" % r)
r=serv.delay()
print("  call processed by: %s" % r)
r=serv.delay()
print("  call processed by: %s" % r)
r=serv.delay()
print("  call processed by: %s" % r)
time.sleep(2)
print("Number of completed calls in the server: %d" % serv.getcount())
print("This should be 10, because by now the 5 oneway calls have completed as well.")
serv.reset()

print("\n--------------------------------------------------------------")
print("    This part depends on the type of the server.              ")
print("--------------------------------------------------------------")
print("Creating 5 threads that each call the server at the same time.")
serverconfig=serv.getconfig()
if serverconfig["SERVERTYPE"]=="thread":
    print("Servertype is thread. All calls will run in parallel.")
    print("The time this will take is 1 second (every thread takes 1 second in parallel).")
    print("You will see that the requests are handled by different server threads.")
elif serverconfig["SERVERTYPE"]=="multiplex":
    print("Servertype is multiplex. The threads will need to get in line.")
    print("The time this will take is 5 seconds (every thread takes 1 second sequentially).")
    print("You will see that the requests are handled by a single server thread.")
else:
    print("Unknown servertype")

def func(uri):
    # This will run in a thread. Create a proxy just for this thread:
    with Pyro4.core.Proxy(uri) as p:
        processed=p.delay()
        print("  thread %s called delay, processed by: %s" % (current_thread().getName(), processed))

serv._pyroBind()  # simplify the uri
threads=[]
for i in range(5):
    t=threadutil.Thread(target=func, args=[serv._pyroUri])
    t.setDaemon(True)
    threads.append(t)
    t.start()
print("Waiting for threads to finish:")
for t in threads:
    t.join()
print("Done. Number of completed calls in the server: %d" % serv.getcount())
