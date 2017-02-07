"""
Pyro MessageBus:  a simple pub/sub message bus.
Provides a way of cummunicating where the sender and receivers are fully decoupled.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""
from __future__ import print_function
import threading
import uuid
import datetime
import time
import logging
import traceback
import sys
from collections import defaultdict
from contextlib import closing
try:
    import cPickle as pickle
except ImportError:
    import pickle
try:
    import sqlite3
except ImportError:
    sqlite3 = None
try:
    import queue
except ImportError:
    import Queue as queue
import Pyro4
import Pyro4.errors
from Pyro4.util import SerializerBase
from . import PYRO_MSGBUS_NAME


__all__ = ["MessageBus", "Message", "SerializerBase"]

log = logging.getLogger("Pyro4.MessageBus")

if sys.version_info >= (3, 0):
    basestring = str


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


@Pyro4.expose
class Subscriber(object):
    def __init__(self, auto_consume=True, max_queue_size=5000):
        self.bus = Pyro4.Proxy("PYRONAME:"+PYRO_MSGBUS_NAME)
        self.received_messages = queue.Queue(maxsize=max_queue_size)
        if auto_consume:
            self.__bus_consumer_thread = threading.Thread(target=self.__bus_consume_message)
            self.__bus_consumer_thread.daemon = True
            self.__bus_consumer_thread.start()

    def incoming_message(self, topic, message):
        self.received_messages.put((topic, message))

    def incoming_messages(self, topic, messages):
        # this is an optimization to receive multiple messages for the topic at the same time
        for msg in messages:
            self.incoming_message(topic, msg)

    def __bus_consume_message(self):
        # this runs in a thread, to pick up and process incoming messages
        while True:
            try:
                topic, message = self.received_messages.get(timeout=1)
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


class MemoryStorage(object):
    """
    Storage implementation that just uses in-memory dicts. It is very fast.
    Stopping the message bus server will make it instantly forget about every topic and pending messages.
    """
    def __init__(self):
        self.messages = {}      # topic -> list of pending messages
        self.subscribers = {}   # topic -> set of subscribers
        self.proxy_cache = {}
        self.total_msg_count = 0

    def topics(self):
        return self.messages.keys()

    def create_topic(self, topic):
        if topic in self.messages:
            return
        self.messages[topic] = []
        self.subscribers[topic] = set()

    def remove_topic(self, topic):
        if topic not in self.messages:
            return
        del self.messages[topic]
        for sub in self.subscribers.get(topic, set()):
            if hasattr(sub, "_pyroRelease"):
                sub._pyroRelease()
            if hasattr(sub, "_pyroUri"):
                try:
                    proxy = self.proxy_cache[sub._pyroUri]
                    proxy._pyroRelease()
                    del self.proxy_cache[sub._pyroUri]
                except KeyError:
                    pass
        del self.subscribers[topic]

    def add_message(self, topic, message):
        self.messages[topic].append(message)
        self.total_msg_count += 1

    def add_subscriber(self, topic, subscriber):
        if hasattr(subscriber, "_pyroUri"):
            # if we already have a subscriber proxy for this uri, use that instead
            subscriber = self.proxy_cache.get(subscriber._pyroUri, subscriber)
            self.proxy_cache[subscriber._pyroUri] = subscriber
        self.subscribers[topic].add(subscriber)

    def remove_subscriber(self, topic, subscriber):
        if subscriber in self.subscribers[topic]:
            if hasattr(subscriber, "_pyroRelease"):
                subscriber._pyroRelease()
            if hasattr(subscriber, "_pyroUri"):
                try:
                    proxy = self.proxy_cache[subscriber._pyroUri]
                    proxy._pyroRelease()
                    del self.proxy_cache[subscriber._pyroUri]
                except KeyError:
                    pass
            self.subscribers[topic].discard(subscriber)

    def all_pending_messages(self):
        return {topic: list(msgs) for topic, msgs in self.messages.items()}

    def has_pending_messages(self, topic):
        return topic in self.messages and any(self.messages[topic])

    def has_subscribers(self, topic):
        return topic in self.subscribers and any(self.subscribers[topic])

    def all_subscribers(self):
        all_subs = {}
        for topic, subs in self.subscribers.items():
            all_subs[topic] = set(subs)
        return all_subs

    def remove_messages(self, topics_messages):
        for topic in topics_messages:
            if topic in self.messages:
                msg_list = self.messages[topic]
                for message in topics_messages[topic]:
                    try:
                        msg_list.remove(message)
                    except ValueError:
                        pass

    def stats(self):
        subscribers = pending = 0
        for subs in self.subscribers.values():
            subscribers += len(subs)
        for msgs in self.messages.values():
            pending += len(msgs)
        return len(self.messages), subscribers, pending, self.total_msg_count


class SqliteStorage(object):
    """
    Storage implementation that uses a sqlite database to store the messages and subscribers.
    It is a lot slower than the in-memory storage, but no data is lost if the messagebus dies.
    If you restart it, it will also reconnect to the subscribers and carry on from where it stopped.
    """
    dbconnections = {}

    def __init__(self):
        conn = self.dbconn()
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("""
CREATE TABLE IF NOT EXISTS Topic (
  id  INTEGER PRIMARY KEY,
  topic  NVARCHAR(500) UNIQUE NOT NULL
); """)
        conn.execute("""
CREATE TABLE IF NOT EXISTS Message(
  id  CHAR(36) PRIMARY KEY,
  created  DATETIME NOT NULL,
  topic  INTEGER NOT NULL,
  msgdata  BLOB NOT NULL,
  FOREIGN KEY(topic) REFERENCES Topic(id)
); """)
        conn.execute("""
CREATE TABLE IF NOT EXISTS Subscription(
  id  INTEGER PRIMARY KEY,
  topic  INTEGER NOT NULL,
  subscriber  NVARCHAR(500) NOT NULL,
  FOREIGN KEY(topic) REFERENCES Topic(id)
); """)
        conn.commit()
        self.proxy_cache = {}
        self.total_msg_count = 0

    def dbconn(self):
        # return the db-connection for the current thread
        thread = threading.current_thread()
        try:
            return self.dbconnections[thread]
        except KeyError:
            conn = sqlite3.connect("messages.sqlite", detect_types=sqlite3.PARSE_DECLTYPES)
            self.dbconnections[thread] = conn
            return conn

    def topics(self):
        conn = self.dbconn()
        with closing(conn.cursor()) as cursor:
            return [r[0] for r in cursor.execute("SELECT topic FROM Topic").fetchall()]

    def create_topic(self, topic):
        conn = self.dbconn()
        with closing(conn.cursor()) as cursor:
            if not cursor.execute("SELECT EXISTS(SELECT 1 FROM Topic WHERE topic=?)", [topic]).fetchone()[0]:
                cursor.execute("INSERT INTO Topic(topic) VALUES(?)", [topic])
        conn.commit()

    def remove_topic(self, topic):
        conn = self.dbconn()
        conn.execute("PRAGMA foreign_keys=ON")
        with closing(conn.cursor()) as cursor:
            topic_id = cursor.execute("SELECT id FROM Topic WHERE topic=?", [topic]).fetchone()
            if not topic_id:
                return
            else:
                topic_id = topic_id[0]
            sub_uris = [r[0] for r in cursor.execute("SELECT subscriber FROM Subscription WHERE topic=?", [topic_id]).fetchall()]
            cursor.execute("DELETE FROM Subscription WHERE topic=?", [topic_id])
            cursor.execute("DELETE FROM Message WHERE topic=?", [topic_id])
            cursor.execute("DELETE FROM Topic WHERE id=?", [topic_id])
        conn.commit()
        for uri in sub_uris:
            try:
                proxy = self.proxy_cache[uri]
                proxy._pyroRelease()
                del self.proxy_cache[uri]
            except KeyError:
                pass

    def add_message(self, topic, message):
        msg_data = pickle.dumps(message.data, pickle.HIGHEST_PROTOCOL)
        if sys.version_info < (3, 0):
            blob_data = buffer(msg_data)
        else:
            blob_data = msg_data
        conn = self.dbconn()
        conn.execute("PRAGMA foreign_keys=ON")
        with closing(conn.cursor()) as cursor:
            res = cursor.execute("SELECT id FROM Topic WHERE topic=?", [topic]).fetchone()
            if not res:
                raise KeyError(topic)
            topic_id = res[0]
            if cursor.execute("SELECT EXISTS(SELECT 1 FROM Subscription WHERE topic=?)", [topic_id]).fetchone()[0]:
                # there is at least one subscriber for this topic, insert the message (otherwise just discard it)
                cursor.execute("INSERT INTO Message(id, created, topic, msgdata) VALUES (?,?,?,?)",
                               [str(message.msgid), message.created, topic_id, blob_data])
        conn.commit()
        self.total_msg_count += 1

    def add_subscriber(self, topic, subscriber):
        if not hasattr(subscriber, "_pyroUri"):
            raise ValueError("can only store subscribers that are a Pyro proxy")
        uri = subscriber._pyroUri.asString()
        conn = self.dbconn()
        conn.execute("PRAGMA foreign_keys=ON")
        with closing(conn.cursor()) as cursor:
            topic_id = cursor.execute("SELECT id FROM Topic WHERE topic=?", [topic]).fetchone()[0]
            if not cursor.execute("SELECT EXISTS(SELECT 1 FROM Subscription WHERE topic=? AND subscriber=?)", [topic_id, uri]).fetchone()[0]:
                cursor.execute("INSERT INTO Subscription(topic, subscriber) VALUES (?,?)", [topic_id, uri])
        self.proxy_cache[uri] = subscriber
        conn.commit()

    def remove_subscriber(self, topic, subscriber):
        conn = self.dbconn()
        conn.execute("PRAGMA foreign_keys=ON")
        uri = subscriber._pyroUri.asString()
        with closing(conn.cursor()) as cursor:
            cursor.execute("DELETE FROM Subscription WHERE topic=(SELECT id FROM Topic WHERE topic=?) AND subscriber=?", [topic, uri])
        conn.commit()
        try:
            proxy = self.proxy_cache[uri]
            proxy._pyroRelease()
            del self.proxy_cache[uri]
        except KeyError:
            pass

    def all_pending_messages(self):
        conn = self.dbconn()
        with closing(conn.cursor()) as cursor:
            msgs = cursor.execute("SELECT t.topic, m.id, m.created, m.msgdata FROM Message AS m, Topic as t WHERE m.topic=t.id").fetchall()
        result = defaultdict(list)
        for msg in msgs:
            if sys.version_info < (3, 0):
                blob_data = str(msg[3])
            else:
                blob_data = msg[3]
            result[msg[0]].append(Message(uuid.UUID(msg[1]), datetime.datetime.strptime(msg[2], "%Y-%m-%d %H:%M:%S.%f"), pickle.loads(blob_data)))
        return result

    def has_pending_messages(self, topic):
        conn = self.dbconn()
        with closing(conn.cursor()) as cursor:
            return cursor.execute("SELECT EXISTS(SELECT 1 FROM Message WHERE topic=(SELECT id FROM Topic WHERE topic=?))", [topic]).fetchone()[0]

    def has_subscribers(self, topic):
        conn = self.dbconn()
        with closing(conn.cursor()) as cursor:
            return cursor.execute("SELECT EXISTS(SELECT 1 FROM Subscription WHERE topic=(SELECT id FROM Topic WHERE topic=?))", [topic]).fetchone()[0]

    def all_subscribers(self):
        conn = self.dbconn()
        with closing(conn.cursor()) as cursor:
            result = cursor.execute("SELECT s.id, t.topic, s.subscriber FROM Subscription AS s, Topic AS t WHERE t.id=s.topic").fetchall()
            subs = defaultdict(list)
            for sub_id, topic, uri in result:
                if uri in self.proxy_cache:
                    proxy = self.proxy_cache[uri]
                    subs[topic].append(proxy)
                else:
                    try:
                        proxy = Pyro4.Proxy(uri)
                    except Exception:
                        log.exception("Cannot create pyro proxy, sub_id=%d, uri=%s", sub_id, uri)
                        cursor.execute("DELETE FROM Subscription WHERE id=?", [sub_id])
                    else:
                        self.proxy_cache[uri] = proxy
                        subs[topic].append(proxy)
        conn.commit()
        return subs

    def remove_messages(self, topics_messages):
        if not topics_messages:
            return
        all_guids = [[str(message.msgid)] for msglist in topics_messages.values() for message in msglist]
        conn = self.dbconn()
        conn.execute("PRAGMA foreign_keys=ON")
        with closing(conn.cursor()) as cursor:
            cursor.executemany("DELETE FROM Message WHERE id = ?", all_guids)
        conn.commit()

    def stats(self):
        conn = self.dbconn()
        with closing(conn.cursor()) as cursor:
            topics = cursor.execute("SELECT COUNT(*) FROM Topic").fetchone()[0]
            subscribers = cursor.execute("SELECT COUNT(*) FROM Subscription").fetchone()[0]
            pending = cursor.execute("SELECT COUNT(*) FROM Message").fetchone()[0]
            return topics, subscribers, pending, self.total_msg_count


def make_messagebus(clazz):
    if make_messagebus.storagetype == "sqlite":
        return clazz(storage=SqliteStorage())
    elif make_messagebus.storagetype == "memory":
        return clazz(storage=MemoryStorage())
    else:
        raise ValueError("invalid storagetype")


@Pyro4.behavior(instance_mode="single", instance_creator=make_messagebus)
@Pyro4.expose
class MessageBus(object):
    def __init__(self, storage=None):
        if storage is None:
            storage = MemoryStorage()
        self.storage = storage     # topic -> list of pending messages
        log.info("using storage: %s", self.storage.__class__.__name__)
        self.msg_lock = threading.Lock()
        self.msg_added = threading.Event()
        self.sender = threading.Thread(target=self.__sender, name="messagebus.sender")
        self.sender.daemon = True
        self.sender.start()
        log.info("started")

    def add_topic(self, topic):
        if not isinstance(topic, basestring):
            raise TypeError("topic must be str")
        with self.msg_lock:
            self.storage.create_topic(topic)

    def remove_topic(self, topic):
        try:
            if self.storage.has_pending_messages(topic) or self.storage.has_subscribers(topic):
                raise ValueError("topic still has pending messages and/or subscribers")
        except KeyError:
            pass
        else:
            with self.msg_lock:
                self.storage.remove_topic(topic)

    def topics(self):
        with self.msg_lock:
            return set(self.storage.topics())

    def send(self, topic, message):
        message = Message(uuid.uuid4(), datetime.datetime.now(), message)
        with self.msg_lock:
            self.storage.add_message(topic, message)
        self.msg_added.set()   # signal that a new message has arrived
        self.msg_added.clear()

    @Pyro4.oneway
    def send_no_ack(self, topic, message):
        self.send(topic, message)

    def subscribe(self, topic, subscriber):
        """Add a subscription to a topic."""
        meth = getattr(subscriber, "incoming_message", None)
        if not meth or not callable(meth):
            raise TypeError("subscriber must have incoming_message() method")
        self.add_topic(topic)   # make sure the topic exists
        with self.msg_lock:
            self.storage.add_subscriber(topic, subscriber)
            log.debug("subscribed: %s -> %s" % (topic, subscriber))

    def unsubscribe(self, topic, subscriber):
        """Remove a subscription to a topic."""
        with self.msg_lock:
            self.storage.remove_subscriber(topic, subscriber)
            log.debug("unsubscribed %s from topic %s" % (subscriber, topic))

    def _unsubscribe_many(self, subscribers):
        if subscribers:
            topics = self.storage.topics()
            with self.msg_lock:
                for topic in topics:
                    for subscriber in subscribers:
                        self.storage.remove_subscriber(topic, subscriber)
            log.debug("unsubscribed from all topics: %s" % subscribers)

    def __sender(self):
        # this runs in a thread, to pick up and forward incoming messages
        prev_print_stats = 0
        while True:
            self.msg_added.wait(timeout=2.01)
            if time.time() - prev_print_stats >= 10:
                prev_print_stats = time.time()
                self._print_stats()
            with self.msg_lock:
                msgs_per_topic = self.storage.all_pending_messages()
                subs_per_topic = self.storage.all_subscribers()
            subs_to_remove = set()
            for topic, messages in msgs_per_topic.items():
                if topic not in subs_per_topic or not messages:
                    continue
                for subscriber in subs_per_topic[topic]:
                    if subscriber in subs_to_remove:
                        # skipping because subscriber is scheduled for removal
                        continue
                    try:
                        try:
                            # send the batch of messages pending for this topic in one go
                            subscriber.incoming_messages(topic, messages)
                        except Pyro4.errors.MessageTooLargeError:
                            # the batch doesn't fit in the configured max msg size, send them one by one instead
                            for message in messages:
                                subscriber.incoming_message(topic, message)
                    except Exception as x:
                        # can't deliver them, drop the subscription
                        log.warning("error delivering message(s) for topic=%s, subscriber=%s, error=%r" % (topic, subscriber, x))
                        log.warning("removing subscription because of that error")
                        subs_to_remove.add(subscriber)
            # remove processed messages
            if msgs_per_topic:
                with self.msg_lock:
                    self.storage.remove_messages(msgs_per_topic)
            # remove broken subscribers
            self._unsubscribe_many(subs_to_remove)

    def _print_stats(self):
        topics, subscribers, pending, messages = self.storage.stats()
        timestamp = datetime.datetime.now()
        timestamp = timestamp.replace(microsecond=0)
        print("\r[%s] stats: %d topics, %d subs, %d pending, %d total     " %
              (timestamp, topics, subscribers, pending, messages), end="")
