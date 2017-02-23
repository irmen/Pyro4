import Pyro4
import Pyro4.util
from customdata import CustomData

# teach Serpent how to deserialize our custom data class
Pyro4.util.SerializerBase.register_dict_to_class(CustomData.serialized_classname, CustomData.from_dict)


class Listener(object):
    def __init__(self, topic):
        self.topic = topic

    def register_with_dispatcher(self):
        with Pyro4.Proxy("PYRONAME:example.blobdispatcher") as dispatcher:
            dispatcher.register(self.topic, self)

    @Pyro4.expose
    def process_blob(self, blob):
        assert blob.info == self.topic
        customdata = blob.deserialized()
        print("Received custom data (type={}):".format(type(customdata)))
        print("    a={}, b={}, c={}".format(customdata.a, customdata.b, customdata.c))
