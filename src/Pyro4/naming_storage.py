"""
Name Server persistent storage implementations.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import re
import logging
import sys
from contextlib import closing
from Pyro4.threadutil import Lock
from Pyro4.errors import NamingError

try:
    import anydbm as dbm   # python 2
except ImportError:
    try:
        import dbm   # python 3
    except ImportError:
        dbm = None
except Exception as x:
    # pypy can generate a distutils error somehow if dbm is not available
    dbm = None

try:
    import sqlite3
except ImportError:
    sqlite3 = None


__all__ = ["SqlStorage", "DbmStorage"]

log = logging.getLogger("Pyro4.naming_storage")


class SqlStorage(object):
    """
    Sqlite-based storage, in just a single (name,uri) table.
    Sqlite db connection objects aren't thread-safe, so a new connection is created in every method.
    """
    def __init__(self, dbfile):
        if dbfile == ":memory:":
            raise ValueError("We don't support the sqlite :memory: database type. Just use the default volatile in-memory store.")
        self.dbfile = dbfile
        with closing(sqlite3.connect(dbfile)) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS pyro_names
                (
                    name nvarchar PRIMARY KEY NOT NULL,
                    uri nvarchar NOT NULL
                );""")
            db.commit()

    def __getattr__(self, item):
        raise NotImplementedError("SqlStorage doesn't implement method/attribute '"+item+"'")

    def __getitem__(self, item):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                result = db.execute("SELECT uri FROM pyro_names WHERE name=?", (item,)).fetchone()
                if result:
                    return result[0]
                else:
                    raise KeyError(item)
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in getitem: "+str(e))

    def __setitem__(self, key, value):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                db.execute("DELETE FROM pyro_names WHERE name=?", (key,))
                db.execute("INSERT INTO pyro_names(name, uri) VALUES(?,?)", (key, value))
                db.commit()
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in setitem: "+str(e))

    def __len__(self):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                return db.execute("SELECT count(*) FROM pyro_names").fetchone()[0]
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in len: "+str(e))

    def __contains__(self, item):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                return db.execute("SELECT EXISTS(SELECT 1 FROM pyro_names WHERE name=? LIMIT 1)", (item,)).fetchone()[0]
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in contains: "+str(e))

    def __delitem__(self, key):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                db.execute("DELETE FROM pyro_names WHERE name=?", (key,))
                db.commit()
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in delitem: "+str(e))

    def __iter__(self):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                result = db.execute("SELECT name FROM pyro_names")
                return iter([n[0] for n in result.fetchall()])
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in iter: "+str(e))

    def clear(self):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                db.execute("DELETE FROM pyro_names")
                db.execute("VACUUM")
                db.commit()
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in clear: "+str(e))

    def optimized_prefix_list(self, prefix):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                result = db.execute("SELECT name, uri FROM pyro_names WHERE name LIKE ?", (prefix+'%',))
                names = {}
                for name, uri in result.fetchall():
                    names[name] = uri
                return names
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in optimized_prefix_list: "+str(e))

    def optimized_regex_list(self, regex):
        # defining a regex function isn't much better than simply regexing ourselves over the full table.
        return None

    def remove_items(self, items):
        try:
            items = [(item,) for item in items]
            with closing(sqlite3.connect(self.dbfile)) as db:
                db.executemany("DELETE FROM pyro_names WHERE name=?", items)
                db.commit()
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in remove_items: "+str(e))

    def everything(self):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                result = db.execute("SELECT name, uri FROM pyro_names")
                names = {}
                for name, uri in result.fetchall():
                    names[name] = uri
                return names
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in everything: "+str(e))

    def close(self):
        pass


class DbmStorage(object):
    """
    Storage implementation that uses a persistent dbm file.
    Because dbm only supports strings as key/value, we encode/decode them in utf-8.
    Dbm files cannot be accessed concurrently, so a strict concurrency model
    is used where only one operation is processed at the same time
    (this is very slow when compared to the in-memory storage)
    """
    def __init__(self, dbmfile):
        self.dbmfile = dbmfile
        db = dbm.open(self.dbmfile, "c", mode=0o600)
        db.close()
        self.lock = Lock()

    def __getattr__(self, item):
        raise NotImplementedError("DbmStorage doesn't implement method/attribute '"+item+"'")

    def __getitem__(self, item):
        item = item.encode("utf-8")
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile)) as db:
                    return db[item].decode("utf-8")
            except dbm.error as e:
                raise NamingError("dbm error in getitem: "+str(e))

    def __setitem__(self, key, value):
        key = key.encode("utf-8")
        value = value.encode("utf-8")
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile, "w")) as db:
                    db[key] = value
            except dbm.error as e:
                raise NamingError("dbm error in setitem: "+str(e))

    def __len__(self):
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile)) as db:
                    return len(db)
            except dbm.error as e:
                raise NamingError("dbm error in len: "+str(e))

    def __contains__(self, item):
        item = item.encode("utf-8")
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile)) as db:
                    return item in db
            except dbm.error as e:
                raise NamingError("dbm error in contains: "+str(e))

    def __delitem__(self, key):
        key = key.encode("utf-8")
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile, "w")) as db:
                    del db[key]
            except dbm.error as e:
                raise NamingError("dbm error in delitem: "+str(e))

    def __iter__(self):
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile)) as db:
                    return iter([key.decode("utf-8") for key in db.keys()])
            except dbm.error as e:
                raise NamingError("dbm error in iter: "+str(e))

    def clear(self):
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile, "w")) as db:
                    if hasattr(db, "clear"):
                        db.clear()
                    else:
                        for key in db.keys():
                            del db[key]
            except dbm.error as e:
                raise NamingError("dbm error in clear: "+str(e))

    def optimized_prefix_list(self, prefix):
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile)) as db:
                    result = {}
                    if hasattr(db, "items"):
                        for key, value in db.items():
                            key = key.decode("utf-8")
                            if key.startswith(prefix):
                                result[key] = value.decode("utf-8")
                    else:
                        for key in db.keys():
                            keystr = key.decode("utf-8")
                            if keystr.startswith(prefix):
                                result[keystr] = db[key].decode("utf-8")
                    return result
            except dbm.error as e:
                raise NamingError("dbm error in optimized_prefix_list: "+str(e))

    def optimized_regex_list(self, regex):
        try:
            regex = re.compile(regex + "$")  # add end of string marker
        except re.error:
            x = sys.exc_info()[1]
            raise NamingError("invalid regex: " + str(x))
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile)) as db:
                    result = {}
                    if hasattr(db, "items"):
                        for key, value in db.items():
                            key = key.decode("utf-8")
                            if regex.match(key):
                                result[key] = value.decode("utf-8")
                    else:
                        for key in db.keys():
                            keystr = key.decode("utf-8")
                            if regex.match(keystr):
                                result[keystr] = db[key].decode("utf-8")
                    return result
            except dbm.error as e:
                raise NamingError("dbm error in optimized_regex_list: "+str(e))

    def remove_items(self, items):
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile, "w")) as db:
                    for item in items:
                        try:
                            del db[item.encode("utf-8")]
                        except KeyError:
                            pass
            except dbm.error as e:
                raise NamingError("dbm error in remove_items: "+str(e))

    def everything(self):
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile)) as db:
                    result = {}
                    if hasattr(db, "items"):
                        for key, value in db.items():
                            result[key.decode("utf-8")] = value.decode("utf-8")
                    else:
                        for key in db.keys():
                            result[key.decode("utf-8")] = db[key].decode("utf-8")
                    return result
            except dbm.error as e:
                raise NamingError("dbm error in everything: "+str(e))

    def close(self):
        pass
