from __future__ import print_function
import threading
import copy
import uuid
import datetime
import logging
import Pyro4
import Pyro4.errors


PYRO_MSGBUS_NAME = "Pyro.MessageBus"

log = logging.getLogger("Pyro.MessageBus")


class MsgbusError(Pyro4.errors.PyroError):
    pass


@Pyro4.expose(instance_mode="single")
class MessageBus(object):
    def __init__(self):
        self.topics = {}        # topic -> list of pending messages
        self.subscribers = {}   # topic -> set of handlers
        self.msg_sema = threading.Semaphore(value=0)
        self.sender = threading.Thread(target=self.__sender, name="messagebus.sender")
        self.sender.daemon = True
        self.sender.start()
        self.msg_lock = threading.Lock()
        self.seq = 1        # global message sequence number
        log.info("started")

    def add_topic(self, topic):
        if topic in self.topics:
            return
        if not isinstance(topic, str):
            raise MsgbusError("topic must be str")
        with self.msg_lock:
            self.topics[topic] = []
            self.subscribers[topic] = set()
        log.debug("topic added: " + topic)

    def remove_topic(self, topic):
        if topic in self.topics:
            if self.topics[topic]:
                raise MsgbusError("topic still has unprocessed messages")
            with self.msg_lock:
                del self.topics[topic]
                del self.subscribers[topic]
            log.debug("topic removed: " + topic)

    def list_topics(self):
        with self.msg_lock:
            return set(self.topics.keys())

    def send_with_ack(self, topic, message):
        message = {
            "msgid": uuid.uuid1(),
            "created": datetime.datetime.now(),
            "seq": -1,
            "data": message,
        }
        if topic not in self.topics:
            self.add_topic(topic)
        with self.msg_lock:
            self.seq += 1
            message["seq"] = self.seq
            self.topics[topic].append(message)
            self.msg_sema.release()

    @Pyro4.oneway
    def send(self, topic, message):
        self.send_with_ack(topic, message)

    def subscribe(self, topic, handler):
        meth = getattr(handler, "handle_message", None)
        if not meth or not callable(meth):
            raise MsgbusError("handler must have callable handle_message() member")
        if hasattr(handler, "_pyroOneway"):
            # make sure that if handler is a pyro proxy, the handle message is a oneway call
            # so that this event processing loop won't block on slow subscribers
            handler._pyroOneway.add("handle_message")
        if topic not in self.topics:
            self.add_topic(topic)
        with self.msg_lock:
            self.subscribers[topic].add(handler)
        log.debug("subscribed: %s -> %s" % (topic, handler))

    def unsubscribe(self, topic, handler):
        if topic in self.subscribers:
            with self.msg_lock:
                self.subscribers[topic].discard(handler)
            log.debug("unsubscribed: %s -> %s" % (topic, handler))

    def __sender(self):
        # this runs in a thread, to pick up and forward incoming messages
        while True:
            self.msg_sema.acquire()
            count_fail = 0
            count_ok = 0
            with self.msg_lock:
                topics = copy.deepcopy(self.topics)
                subs = copy.copy(self.subscribers)
            subs_to_remove = []
            for topic, messages in topics.items():
                if topic in subs:
                    handlers = subs[topic]
                    for message in messages:
                        for handler in handlers:
                            try:
                                handler.handle_message(topic, **message)
                                count_ok += 1
                            except Pyro4.errors.CommunicationError as x:
                                # can't connect, drop the message and the handler subscription
                                log.warn("communication error for topic=%s, msgid=%s, seq=%d, handler=%s, error=%r" %
                                         (topic, message["msgid"], message["seq"], handler, x))
                                log.warn("removing subscription for handler because of that error")
                                subs_to_remove.append((topic, handler))
                                count_fail += 1
                            except Exception as x:
                                # something went wrong, drop the message
                                log.warn("processing failed for topic=%s, msgid=%s, seq=%d, handler=%s, error=%r" %
                                         (topic, message["msgid"], message["seq"], handler, x))
                                count_fail += 1
            # remove processed messages
            with self.msg_lock:
                for topic in topics:
                    if topic in self.topics:
                        msg_list = self.topics[topic]
                        for message in topics[topic]:
                            try:
                                msg_list.remove(message)
                            except KeyError:
                                pass
            # remove broken subbers
            for topic, handler in subs_to_remove:
                self.unsubscribe(topic, handler)
            #if count_fail + count_ok > 0:
            #    log.debug("sent %d messages, %d failed" % (count_ok, count_fail))


@Pyro4.expose()
class Subscriber(object):
    def __init__(self):
        self.bus = Pyro4.Proxy("PYRONAME:"+PYRO_MSGBUS_NAME)

    @Pyro4.oneway
    def handle_message(self, topic, msgid, seq, created, data):
        raise NotImplementedError("implement in subclass")


if __name__ == "__main__":
    Pyro4.Daemon.serveSimple({
        MessageBus: PYRO_MSGBUS_NAME
    })
