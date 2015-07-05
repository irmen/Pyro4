from __future__ import print_function
import threading
import sys
import traceback
import time
import logging
import uuid
import datetime
try:
    import queue
except ImportError:
    import Queue as queue
import Pyro4
import Pyro4.errors
from Pyro4.util import SerializerBase
from . import PYRO_MSGBUS_NAME

__all__ = ["Subscriber", "Message"]

log = logging.getLogger("Pyro.MessageBus")


class Message(object):
    __slots__ = ("msgid", "created", "data")

    def __init__(self, msgid, created, data):
        self.msgid = msgid
        self.created = created
        self.data = data

    @staticmethod
    def to_dict(obj):
        return {
            "__class__": "Pyro4.utils.messagebus.message",
            "msgid": str(obj.msgid),
            "created": obj.created.isoformat(),
            "data": obj.data
        }

    @classmethod
    def from_dict(cls, classname, d):
        return cls(uuid.UUID(d["msgid"]),
                   datetime.datetime.strptime(d["created"], "%Y-%m-%dT%H:%M:%S.%f"),
                   d["data"])

# make sure Pyro knows how to serialize the custom Message class
SerializerBase.register_class_to_dict(Message, Message.to_dict)
SerializerBase.register_dict_to_class("Pyro4.utils.messagebus.message", Message.from_dict)


@Pyro4.expose()
class Subscriber(object):
    def __init__(self):
        self.bus = Pyro4.Proxy("PYRONAME:"+PYRO_MSGBUS_NAME)
        self.messages = queue.Queue()
        self.consumer_thread = threading.Thread(target=self.__consume_message)
        self.consumer_thread.daemon = True
        self.consumer_thread.start()

    def incoming_message(self, topic, message):
        self.messages.put((topic, message))

    def __consume_message(self):
        # this runs in a thread, to pick up and process incoming messages
        while True:
            try:
                topic, message = self.messages.get(timeout=1)
            except queue.Empty:
                time.sleep(0.002)
                continue
            try:
                self.consume_message(topic, message)
            except Exception:
                print("Error while consuming message:", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

    def consume_message(self, topic, message):
        # this is called from a background thread
        raise NotImplementedError("subclass should implement this")
