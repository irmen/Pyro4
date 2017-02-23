from __future__ import print_function
from collections import defaultdict
import Pyro4

# note: the dispatcher doesn't know anything about the CustomData class from the customdata module!


@Pyro4.behavior(instance_mode="single")
class Dispatcher(object):
    def __init__(self):
        self.listeners = defaultdict(list)

    @Pyro4.expose
    def register(self, topic, listener):
        self.listeners[topic].append(listener)
        print("New listener for topic {} registered: {}".format(topic, listener._pyroUri))

    @Pyro4.expose
    def process_blob(self, blob):
        print("Dispatching blob with name:", blob.info)
        listeners = self.listeners.get(blob.info, [])
        for listener in listeners:
            listener.process_blob(blob)


Pyro4.Daemon.serveSimple({
    Dispatcher: "example.blobdispatcher"
})
