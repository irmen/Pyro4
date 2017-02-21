from __future__ import print_function
import sys
import datetime
import Pyro4.util
import Pyro4.core
import Pyro4
from customdata import CustomData

if sys.version_info < (3, 0):
    input = raw_input


sys.excepthook = Pyro4.util.excepthook

# teach Serpent how to serialize our data class
Pyro4.util.SerializerBase.register_class_to_dict(CustomData, CustomData.to_dict)


with Pyro4.Proxy("PYRONAME:example.blobdispatcher") as dispatcher:
    while True:
        topic = input("Enter topic to send data on (just enter to quit) ").strip()
        if not topic:
            break
        # create our custom data object and send it through the dispatcher
        data = CustomData(42, "hello world", datetime.datetime.now())
        dispatcher.process_blob(Pyro4.core.SerializedBlob(topic, data))
        print("processed")
