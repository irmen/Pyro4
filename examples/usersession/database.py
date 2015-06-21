from __future__ import print_function
import threading
import time
import random
import traceback


class DummyDatabase(object):
    """Key-value datastore"""
    def __init__(self):
        self.storage = {}
        self.allowed_users = ["user123", "admin"]

    def connect(self, user):
        return Connection(self, user)

    def __setitem__(self, key, value):
        time.sleep(random.random()/10)   # artificial delay
        self.storage[key] = value

    def __getitem__(self, item):
        time.sleep(random.random()/10)   # artificial delay
        return self.storage[item]


class Connection(object):
    """
    Connection to the key-value datastore with artificial limitation
    that only a single thread may use the connection at the same time
    """
    def __init__(self, db, user=None):
        self.db = db
        self.user = user
        self.lock = threading.RLock()

    def store(self, key, value, user=None):
        user = user or self.user
        assert user in self.db.allowed_users, "access denied"
        if self.lock.acquire(blocking=False):
            print("DB: user %s stores: %s = %s" % (user, key, value))
            self.db[key] = value
            self.lock.release()
        else:
            raise RuntimeError("ERROR: concurrent connection access (write) by multiple different threads")

    def retrieve(self, key, user=None):
        user = user or self.user
        assert user in self.db.allowed_users, "access denied"
        if self.lock.acquire(blocking=False):
            print("DB: user %s retrieve: %s" % (user, key))
            value = self.db[key]
            self.lock.release()
            return value
        else:
            raise RuntimeError("ERROR: concurrent connection access (read) by multiple different threads")


if __name__ == "__main__":
    # first single threaded access
    db = DummyDatabase()
    conn = db.connect("user123")
    for i in range(5):
        conn.store("amount", 100+i)
        conn.retrieve("amount")

    # now multiple threads, should crash

    class ClientThread(threading.Thread):
        def __init__(self, conn):
            super(ClientThread, self).__init__()
            self.conn = conn
            self.daemon = True
        def run(self):
            for i in range(5):
                try:
                    self.conn.store("amount", 100+i)
                except Exception:
                    traceback.print_exc()
                try:
                    self.conn.retrieve("amount")
                except Exception:
                    traceback.print_exc()

    client1 = ClientThread(conn)
    client2 = ClientThread(conn)
    client1.start()
    client2.start()
    time.sleep(0.1)
    client1.join()
    client2.join()
