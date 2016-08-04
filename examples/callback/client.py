import random
import Pyro4


# We need to set either a socket communication timeout,
# or use the select based server. Otherwise the daemon requestLoop
# will block indefinitely and is never able to evaluate the loopCondition.
Pyro4.config.COMMTIMEOUT = 0.5

NUM_WORKERS = 5


class CallbackHandler(object):
    workdone = 0

    @Pyro4.expose
    def done(self, number):
        print("callback: worker %d reports work is done!" % number)
        CallbackHandler.workdone += 1


with Pyro4.core.Daemon() as daemon:
    # register our callback handler
    callback = CallbackHandler()
    daemon.register(callback)

    # contact the server and put it to work
    print("creating a bunch of workers")
    with Pyro4.core.Proxy("PYRONAME:example.callback") as server:
        for _ in range(NUM_WORKERS):
            worker = server.addworker(callback)  # provide our callback handler!
            worker.work(random.randint(1, 5))

    print("waiting for all work complete...")
    daemon.requestLoop(loopCondition=lambda: CallbackHandler.workdone < NUM_WORKERS)
    print("done!")
