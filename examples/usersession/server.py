from __future__ import print_function
import Pyro4
from database import DummyDatabase


Pyro4.config.SERVERTYPE = "thread"
database = DummyDatabase()


@Pyro4.behavior(instance_mode="single")
@Pyro4.expose
class SingletonDatabase(object):
    """
    This pyro object will exhibit problems when used from multiple proxies at the same time
    because it will access the database connection concurrently from different threads
    """
    def __init__(self):
        print("[%s] new instance and connection" % self.__class__.__name__)
        self.conn = database.connect(user=None)  # user is per-call, not global

    def store(self, key, value):
        # get the user-token from the USER annotation
        ctx = Pyro4.current_context
        user = ctx.annotations["USER"].decode("utf-8")
        self.conn.store(key, value, user=user)

    def retrieve(self, key):
        # get the user-token from the USER annotation
        ctx = Pyro4.current_context
        user = ctx.annotations["USER"].decode("utf-8")
        return self.conn.retrieve(key, user=user)

    def ping(self):
        return "hi"


@Pyro4.behavior(instance_mode="session")
@Pyro4.expose
class SessionboundDatabase(object):
    """
    This pyro object will work fine when used from multiple proxies at the same time
    because you'll get a new instance for every new session (proxy connection)
    """
    def __init__(self):
        # get the user-token from the USER annotation
        ctx = Pyro4.current_context
        user = ctx.annotations["USER"].decode("utf-8")
        self.connection = database.connect(user)
        print("[%s] new instance and connection for user: %s" % (self.__class__.__name__, user))

    def store(self, key, value):
        self.connection.store(key, value)

    def retrieve(self, key):
        return self.connection.retrieve(key)

    def ping(self):
        return "hi"


Pyro4.Daemon.serveSimple({
    SingletonDatabase: "example.usersession.singletondb",
    SessionboundDatabase: "example.usersession.sessiondb"
})
