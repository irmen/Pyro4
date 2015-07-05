from __future__ import print_function
import threading
import uuid
import datetime
import time
import logging
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
import Pyro4
import Pyro4.errors
from .client import Message
from . import PYRO_MSGBUS_NAME


__all__ = ["MemoryStorage", "SqliteStorage", "MessageBus"]

log = logging.getLogger("Pyro.MessageBus")
Pyro4.config.COMMTIMEOUT = 30.0
Pyro4.config.POLLTIMEOUT = 10.0
Pyro4.config.MAX_MESSAGE_SIZE = 256*1024     # 256 kb
Pyro4.config.MAX_RETRIES = 3


class MemoryStorage(object):
    """
    Storage implementation that just uses in-memory dicts. It is very fast.
    Stopping the message bus server will make it instantly forget about every topic and pending messages.
    """
    def __init__(self):
        self.messages = {}      # topic -> list of pending messages
        self.subscribers = {}   # topic -> set of subscribers
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
        del self.subscribers[topic]

    def add_message(self, topic, message):
        self.messages[topic].append(message)
        self.total_msg_count += 1

    def add_subscriber(self, topic, subscriber):
        self.subscribers[topic].add(subscriber)

    def remove_subscriber(self, topic, subscriber):
        if subscriber in self.subscribers[topic]:
            if hasattr(subscriber, "_pyroRelease"):
                subscriber._pyroRelease()
            self.subscribers[topic].discard(subscriber)

    def all_pending_messages(self):
        return {topic: msgs.copy() for topic, msgs in self.messages.items()}

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
                        import pdb
                        pdb.set_trace()
                        raise  # XXX
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
        conn.execute("PRAGMA foreign_keys = ON;")
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
        topics = self.topics()
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
            topics = [r[0] for r in cursor.execute("SELECT topic FROM Topic").fetchall()]
        conn.commit()
        return topics

    def create_topic(self, topic):
        conn = self.dbconn()
        with closing(conn.cursor()) as cursor:
            if not cursor.execute("SELECT EXISTS(SELECT 1 FROM Topic WHERE topic=?)", [topic]).fetchone()[0]:
                cursor.execute("INSERT INTO Topic(topic) VALUES(?)", [topic])
        conn.commit()

    def remove_topic(self, topic):
        conn = self.dbconn()
        with closing(conn.cursor()) as cursor:
            topic_id = cursor.execute("SELECT id FROM Topic WHERE topic=?", [topic]).fetchone([0])
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
        conn = self.dbconn()
        with closing(conn.cursor()) as cursor:
            topic_id = cursor.execute("SELECT id FROM Topic WHERE topic=?", [topic]).fetchone()[0]
            if cursor.execute("SELECT EXISTS(SELECT 1 FROM Subscription WHERE topic=?)", [topic_id]).fetchone()[0]:
                # there is at least one subscriber for this topic, insert the message (otherwise just discard it)
                cursor.execute("INSERT INTO Message(id, created, topic, msgdata) VALUES (?,?,?,?)",
                               [str(message.msgid), message.created, topic_id, msg_data])
        conn.commit()
        self.total_msg_count += 1

    def add_subscriber(self, topic, subscriber):
        if not hasattr(subscriber, "_pyroUri"):
            raise ValueError("can only store subscribers that are a Pyro proxy")
        uri = subscriber._pyroUri.asString()
        conn = self.dbconn()
        with closing(conn.cursor()) as cursor:
            cursor.execute("INSERT INTO Subscription(topic, subscriber) VALUES ((SELECT id FROM Topic WHERE topic=?),?)", [topic, uri])
        self.proxy_cache[uri] = subscriber
        conn.commit()

    def remove_subscriber(self, topic, subscriber):
        conn = self.dbconn()
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
        conn.commit()
        result = defaultdict(list)
        for msg in msgs:
            result[msg[0]].append(Message(uuid.UUID(msg[1]), datetime.datetime.strptime(msg[2], "%Y-%m-%d %H:%M:%S.%f"), pickle.loads(msg[3])))
        return result

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
        with closing(conn.cursor()) as cursor:
            cursor.executemany("DELETE FROM Message WHERE id = ?", all_guids)
        conn.commit()

    def stats(self):
        conn = self.dbconn()
        with closing(conn.cursor()) as cursor:
            topics = cursor.execute("SELECT COUNT(*) FROM Topic").fetchone()[0]
            subscribers = cursor.execute("SELECT COUNT(*) FROM Subscription").fetchone()[0]
            pending = cursor.execute("SELECT COUNT(*) FROM Message").fetchone()[0]
        conn.commit()
        return topics, subscribers, pending, self.total_msg_count


def make_messagebus(clazz):
    if make_messagebus.storagetype == "sqlite":
        storage = SqliteStorage()
    elif make_messagebus.storagetype == "memory":
        storage = MemoryStorage()
    else:
        raise ValueError("invalid storagetype")
    return clazz(storage=storage)


@Pyro4.expose(instance_mode="single", instance_creator=make_messagebus)
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
        if not isinstance(topic, str):
            raise TypeError("topic must be str")
        with self.msg_lock:
            self.storage.create_topic(topic)

    def remove_topic(self, topic):
        if self.storage.has_pending_messages(topic):
            raise ValueError("topic still has pending messages")
        with self.msg_lock:
            self.storage.remove_topic(topic)

    def list_topics(self):
        with self.msg_lock:
            return self.storage.topics()

    def send(self, topic, message):
        message = Message(uuid.uuid1(), datetime.datetime.now(), message)
        self.add_topic(topic)
        with self.msg_lock:
            self.storage.add_message(topic, message)
        self.msg_added.set()   # signal that a new message has arrived
        self.msg_added.clear()

    @Pyro4.oneway
    def send_no_ack(self, topic, message):
        self.send(topic, message)

    def subscribe(self, topic, subscriber):
        meth = getattr(subscriber, "incoming_message", None)
        if not meth or not callable(meth):
            raise TypeError("subscriber must have incoming_message() method")
        self.add_topic(topic)
        with self.msg_lock:
            self.storage.add_subscriber(topic, subscriber)
        log.debug("subscribed: %s -> %s" % (topic, subscriber))

    def unsubscribe(self, topic, subscriber):
        self.unsubscribe_many([(topic, subscriber)])

    def unsubscribe_many(self, subs):
        if subs:
            with self.msg_lock:
                for topic, subscriber in subs:
                    self.storage.remove_subscriber(topic, subscriber)
                    log.debug("unsubscribed: %s -> %s" % (topic, subscriber))

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
                if topic in subs_per_topic:
                    subscribers = subs_per_topic[topic]
                    for message in messages:
                        for subscriber in subscribers:
                            if (topic, subscriber) in subs_to_remove:
                                # skipping because subber is scheduled for removal
                                continue
                            try:
                                subscriber.incoming_message(topic, message)
                            except Exception as x:
                                # can't deliver it, drop the message and the subscription
                                log.warn("error delivering message for topic=%s, msgid=%s, subscriber=%s, error=%r" %
                                         (topic, message.msgid, subscriber, x))
                                log.warn("removing subscription because of that error")
                                subs_to_remove.add((topic, subscriber))
            # remove processed messages
            if msgs_per_topic:
                with self.msg_lock:
                    self.storage.remove_messages(msgs_per_topic)
            # remove broken subbers
            self.unsubscribe_many(subs_to_remove)

    def _print_stats(self):
        topics, subscribers, pending, messages = self.storage.stats()
        timestamp = datetime.datetime.now()
        timestamp = timestamp.replace(microsecond=0)
        print("\r[%s] stats: %d topics, %d subs, %d pending, %d total     " %
              (timestamp, topics, subscribers, pending, messages), end="")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("provide storage type as argument (sqlite/memory)")
    if sys.argv[1] not in ("sqlite", "memory"):
        raise ValueError("invalid storagetype")
    make_messagebus.storagetype = sys.argv[1]
    Pyro4.Daemon.serveSimple({
        MessageBus: PYRO_MSGBUS_NAME
    })
