from __future__ import print_function
import threading
import copy
import uuid
import datetime
import logging
from collections import MutableMapping
from contextlib import closing
try:
    import sqlite3
except ImportError:
    sqlite3 = None
import Pyro4
import Pyro4.errors


PYRO_MSGBUS_NAME = "Pyro.MessageBus"

log = logging.getLogger("Pyro.MessageBus")


class MsgbusError(Pyro4.errors.PyroError):
    pass


class MemoryStorage(dict):
    """
    Storage implementation that is just an in-memory dict.
    (because it inherits from dict it is automatically a collections.MutableMapping)
    Stopping the message bus server will make it instantly forget about every topic and pending messages.
    """
    def __init__(self):
        super(MemoryStorage, self).__init__()

    def add_message(self, topic, message):
        self.__getitem__(topic).append(message)

    def get_all_pending_messages(self):
        return copy.deepcopy(dict(self))

    def remove_messages(self, topics_messages):
        for topic in topics_messages:
            if topic in self:
                msg_list = self[topic]
                for message in topics_messages[topic]:
                    try:
                        msg_list.remove(message)
                    except KeyError:
                        pass


class SqliteStorage(MutableMapping):
    def __init__(self, dblocation):
        super(SqliteStorage, self).__init__()
        if dblocation == ":memory:":
            raise ValueError("We don't support the sqlite :memory: database type. Just use the default volatile in-memory store.")
        self.dblocation = dblocation
        conn = self.get_db_conn()
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("""
CREATE TABLE IF NOT EXISTS Topic (
  id  INTEGER PRIMARY KEY NOT NULL,
  topic  NVARCHAR(500) UNIQUE NOT NULL
); """)
        conn.execute("""
CREATE TABLE IF NOT EXISTS Message(
  id  CHAR(36) PRIMARY KEY NOT NULL,
  created  DATETIME NOT NULL,
  seq  INTEGER NOT NULL,
  topic  INTEGER NOT NULL,
  msgdata  BLOB NOT NULL,
  FOREIGN KEY(topic) REFERENCES Topic(id)
); """)
        conn.commit()

    def get_db_conn(self):
        return sqlite3.connect(self.dblocation, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)

    def __delitem__(self, topic):
        with self.get_db_conn() as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute("DELETE FROM Topic WHERE topic=?", [topic])
            conn.commit()

    def __len__(self):
        with self.get_db_conn() as conn:
            with closing(conn.cursor()) as cursor:
                return cursor.execute("SELECT COUNT(*) FROM Topic").fetchone()[0]

    def __setitem__(self, topic, messages):
        if messages:
            raise ValueError("only supports creating a new topic with 0 pending messages")
        with self.get_db_conn() as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute("INSERT INTO Topic(topic) VALUES(?)", [topic])
            conn.commit()

    def __getitem__(self, topic):
        with self.get_db_conn() as conn:
            with closing(conn.cursor()) as cursor:
                results = SqliteStorage._fetch_messages(cursor, topic)
        return (SqliteStorage._map_message(r) for r in results)

    @staticmethod
    def _fetch_messages(cursor, topic):
        return cursor.execute("SELECT m.id, m.created, m.seq, m.msgdata FROM Message AS m, Topic as t WHERE m.topic=t.id AND t.topic=?", [topic]).fetchall()

    @staticmethod
    def _map_message(dbcolums):
        return {"msgid": uuid.UUID(dbcolums[0]),
                "created": datetime.datetime.strptime(dbcolums[1], "%Y-%m-%d %H:%M:%S.%f"),
                "seq": dbcolums[2],
                "data": dbcolums[3]}

    def __iter__(self):
        with self.get_db_conn() as conn:
            with closing(conn.cursor()) as cursor:
                results = cursor.execute("SELECT topic FROM Topic").fetchall()
        return (r[0] for r in results)

    def __contains__(self, topic):
        with self.get_db_conn() as conn:
            with closing(conn.cursor()) as cursor:
                return bool(cursor.execute("SELECT EXISTS (SELECT 1 FROM Topic WHERE topic=?)", [topic]).fetchone()[0])

    def add_message(self, topic, message):
        with self.get_db_conn() as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute("INSERT INTO Message(id, created, seq, topic, msgdata) VALUES (?,?,?, (SELECT id FROM Topic WHERE topic=?), ?)",
                               [str(message["msgid"]), message["created"], message["seq"], topic, message["data"]])
            conn.commit()

    def get_all_pending_messages(self):
        with self.get_db_conn() as conn:
            with closing(conn.cursor()) as cursor:
                topics = (r[0] for r in cursor.execute("SELECT topic FROM Topic").fetchall())
                result = {topic: [SqliteStorage._map_message(r) for r in SqliteStorage._fetch_messages(cursor, topic)] for topic in topics}
                return result

    def remove_messages(self, topics_messages):
        all_guids = [[str(message["msgid"])] for msglist in topics_messages.values() for message in msglist]
        with self.get_db_conn() as conn:
            with closing(conn.cursor()) as cursor:
                cursor.executemany("DELETE FROM Message WHERE id = ?", all_guids)


def make_messagebus():
    storage = SqliteStorage("messages.sqlite")
    return MessageBus(storage=storage)


@Pyro4.expose(instance_mode="single", instance_creator=make_messagebus)
class MessageBus(object):
    def __init__(self, storage=None):
        if storage is None:
            storage = MemoryStorage()
        self.messages_for_topics = storage     # topic -> list of pending messages
        log.info("using storage: %s", self.messages_for_topics.__class__.__name__)
        self.msg_lock = threading.Lock()
        self.msg_sema = threading.Semaphore(value=0)
        self.subscribers = {topic: set() for topic in self.messages_for_topics}   # topic -> set of handlers
        self.sender = threading.Thread(target=self.__sender, name="messagebus.sender")
        self.sender.daemon = True
        self.sender.start()
        self.seq = 1        # global message sequence number
        log.info("started")

    def add_topic(self, topic):
        if topic in self.messages_for_topics:
            return
        if not isinstance(topic, str):
            raise MsgbusError("topic must be str")
        with self.msg_lock:
            self.messages_for_topics[topic] = []
            self.subscribers[topic] = set()
        log.debug("topic added: " + topic)

    def remove_topic(self, topic):
        if topic in self.messages_for_topics:
            if self.messages_for_topics[topic]:
                raise MsgbusError("topic still has unprocessed messages")
            with self.msg_lock:
                del self.messages_for_topics[topic]
                del self.subscribers[topic]
            log.debug("topic removed: " + topic)

    def list_topics(self):
        with self.msg_lock:
            return set(self.messages_for_topics.keys())

    def send_with_ack(self, topic, message):
        message = {
            "msgid": uuid.uuid1(),
            "created": datetime.datetime.now(),
            "seq": -1,
            "data": message,
        }
        if topic not in self.messages_for_topics:
            self.add_topic(topic)
        with self.msg_lock:
            self.seq += 1
            message["seq"] = self.seq
            self.messages_for_topics.add_message(topic, message)
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
        if topic not in self.messages_for_topics:
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
                topics = self.messages_for_topics.get_all_pending_messages()
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
                self.messages_for_topics.remove_messages(topics)
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
