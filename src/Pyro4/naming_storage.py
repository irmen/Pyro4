"""
Name Server persistent storage implementations.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import re
import logging
import sys
import threading
if sys.version_info <= (3, 4):
    from collections import MutableMapping
else:
    from collections.abc import MutableMapping
from contextlib import closing
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


log = logging.getLogger("Pyro4.naming_storage")


class SqlStorage(MutableMapping):
    """
    Sqlite-based storage.
    It is just a single (name,uri) table for the names and another table for the metadata.
    Sqlite db connection objects aren't thread-safe, so a new connection is created in every method.
    """
    def __init__(self, dbfile):
        if dbfile == ":memory:":
            raise ValueError("We don't support the sqlite :memory: database type. Just use the default volatile in-memory store.")
        self.dbfile = dbfile
        with closing(sqlite3.connect(dbfile)) as db:
            db.execute("PRAGMA foreign_keys=ON")
            try:
                db.execute("SELECT COUNT(*) FROM pyro_names").fetchone()
            except sqlite3.OperationalError:
                # the table does not yet exist
                self._create_schema(db)
            else:
                # check if we need to update the existing schema
                try:
                    db.execute("SELECT COUNT(*) FROM pyro_metadata").fetchone()
                except sqlite3.OperationalError:
                    # metadata schema needs to be created and existing data migrated
                    db.execute("ALTER TABLE pyro_names RENAME TO pyro_names_old")
                    self._create_schema(db)
                    db.execute("INSERT INTO pyro_names(name, uri) SELECT name, uri FROM pyro_names_old")
                    db.execute("DROP TABLE pyro_names_old")
            db.commit()

    def _create_schema(self, db):
        db.execute("""CREATE TABLE pyro_names
            (
                id integer PRIMARY KEY,
                name nvarchar NOT NULL UNIQUE,
                uri nvarchar NOT NULL
            );""")
        db.execute("""CREATE TABLE pyro_metadata
            (
                object integer NOT NULL,
                metadata nvarchar NOT NULL,
                FOREIGN KEY(object) REFERENCES pyro_names(id)
            );""")

    def __getattr__(self, item):
        raise NotImplementedError("SqlStorage doesn't implement method/attribute '" + item + "'")

    def __getitem__(self, item):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                result = db.execute("SELECT id, uri FROM pyro_names WHERE name=?", (item,)).fetchone()
                if result:
                    dbid, uri = result
                    metadata = {m[0] for m in db.execute("SELECT metadata FROM pyro_metadata WHERE object=?", (dbid,)).fetchall()}
                    return uri, metadata
                else:
                    raise KeyError(item)
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in getitem: " + str(e))

    def __setitem__(self, key, value):
        uri, metadata = value
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                cursor = db.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                dbid = cursor.execute("SELECT id FROM pyro_names WHERE name=?", (key,)).fetchone()
                if dbid:
                    dbid = dbid[0]
                    cursor.execute("DELETE FROM pyro_metadata WHERE object=?", (dbid,))
                    cursor.execute("DELETE FROM pyro_names WHERE id=?", (dbid,))
                cursor.execute("INSERT INTO pyro_names(name, uri) VALUES(?,?)", (key, uri))
                if metadata:
                    object_id = cursor.lastrowid
                    for m in metadata:
                        cursor.execute("INSERT INTO pyro_metadata(object, metadata) VALUES (?,?)", (object_id, m))
                cursor.close()
                db.commit()
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in setitem: " + str(e))

    def __len__(self):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                return db.execute("SELECT count(*) FROM pyro_names").fetchone()[0]
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in len: " + str(e))

    def __contains__(self, item):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                return db.execute("SELECT EXISTS(SELECT 1 FROM pyro_names WHERE name=? LIMIT 1)", (item,)).fetchone()[0]
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in contains: " + str(e))

    def __delitem__(self, key):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                db.execute("PRAGMA foreign_keys=ON")
                dbid = db.execute("SELECT id FROM pyro_names WHERE name=?", (key,)).fetchone()
                if dbid:
                    dbid = dbid[0]
                    db.execute("DELETE FROM pyro_metadata WHERE object=?", (dbid,))
                    db.execute("DELETE FROM pyro_names WHERE id=?", (dbid,))
                db.commit()
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in delitem: " + str(e))

    def __iter__(self):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                result = db.execute("SELECT name FROM pyro_names")
                return iter([n[0] for n in result.fetchall()])
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in iter: " + str(e))

    def clear(self):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                db.execute("PRAGMA foreign_keys=ON")
                db.execute("DELETE FROM pyro_metadata")
                db.execute("DELETE FROM pyro_names")
                db.commit()
            with closing(sqlite3.connect(self.dbfile, isolation_level=None)) as db:
                db.execute("VACUUM")  # this cannot run inside a transaction.
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in clear: " + str(e))

    def optimized_prefix_list(self, prefix, return_metadata=False):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                names = {}
                if return_metadata:
                    for dbid, name, uri in db.execute("SELECT id, name, uri FROM pyro_names WHERE name LIKE ?", (prefix + '%',)).fetchall():
                        metadata = {m[0] for m in db.execute("SELECT metadata FROM pyro_metadata WHERE object=?", (dbid,)).fetchall()}
                        names[name] = uri, metadata
                else:
                    for name, uri in db.execute("SELECT name, uri FROM pyro_names WHERE name LIKE ?", (prefix + '%',)).fetchall():
                        names[name] = uri
                return names
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in optimized_prefix_list: " + str(e))

    def optimized_regex_list(self, regex, return_metadata=False):
        # defining a regex function isn't much better than simply regexing ourselves over the full table.
        return None

    def optimized_metadata_search(self, metadata_all=None, metadata_any=None, return_metadata=False):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                if metadata_any:
                    # any of the given metadata
                    params = list(metadata_any)
                    sql = "SELECT id, name, uri FROM pyro_names WHERE id IN (SELECT object FROM pyro_metadata WHERE metadata IN ({seq}))" \
                          .format(seq=",".join(['?'] * len(metadata_any)))
                else:
                    # all of the given metadata
                    params = list(metadata_all)
                    params.append(len(metadata_all))
                    sql = "SELECT id, name, uri FROM pyro_names WHERE id IN (SELECT object FROM pyro_metadata WHERE metadata IN ({seq}) " \
                          "GROUP BY object HAVING COUNT(metadata)=?)".format(seq=",".join(['?'] * len(metadata_all)))
                result = db.execute(sql, params).fetchall()
                if return_metadata:
                    names = {}
                    for dbid, name, uri in result:
                        metadata = {m[0] for m in db.execute("SELECT metadata FROM pyro_metadata WHERE object=?", (dbid,)).fetchall()}
                        names[name] = uri, metadata
                else:
                    names = {name: uri for (dbid, name, uri) in result}
                return names
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in optimized_metadata_search: " + str(e))

    def remove_items(self, items):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                db.execute("PRAGMA foreign_keys=ON")
                for item in items:
                    dbid = db.execute("SELECT id FROM pyro_names WHERE name=?", (item,)).fetchone()
                    if dbid:
                        dbid = dbid[0]
                        db.execute("DELETE FROM pyro_metadata WHERE object=?", (dbid,))
                        db.execute("DELETE FROM pyro_names WHERE id=?", (dbid,))
                db.commit()
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in remove_items: " + str(e))

    def everything(self, return_metadata=False):
        try:
            with closing(sqlite3.connect(self.dbfile)) as db:
                names = {}
                if return_metadata:
                    for dbid, name, uri in db.execute("SELECT id, name, uri FROM pyro_names").fetchall():
                        metadata = {m[0] for m in db.execute("SELECT metadata FROM pyro_metadata WHERE object=?", (dbid,)).fetchall()}
                        names[name] = uri, metadata
                else:
                    for name, uri in db.execute("SELECT name, uri FROM pyro_names").fetchall():
                        names[name] = uri
                return names
        except sqlite3.DatabaseError as e:
            raise NamingError("sqlite error in everything: " + str(e))

    def close(self):
        pass


class DbmStorage(MutableMapping):
    """
    Storage implementation that uses a persistent dbm file.
    Because dbm only supports strings as key/value, we encode/decode them in utf-8.
    Dbm files cannot be accessed concurrently, so a strict concurrency model
    is used where only one operation is processed at the same time
    (this is very slow when compared to the in-memory storage)
    DbmStorage does NOT support storing metadata! It only accepts empty metadata,
    and always returns empty metadata.
    """
    def __init__(self, dbmfile):
        self.dbmfile = dbmfile
        db = dbm.open(self.dbmfile, "c", mode=0o600)
        db.close()
        self.lock = threading.Lock()

    def __getattr__(self, item):
        raise NotImplementedError("DbmStorage doesn't implement method/attribute '" + item + "'")

    def __getitem__(self, item):
        item = item.encode("utf-8")
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile)) as db:
                    return db[item].decode("utf-8"), frozenset()    # always return empty metadata
            except dbm.error as e:
                raise NamingError("dbm error in getitem: " + str(e))

    def __setitem__(self, key, value):
        uri, metadata = value
        if metadata:
            log.warning("DbmStorage doesn't support metadata, silently discarded")
        key = key.encode("utf-8")
        uri = uri.encode("utf-8")
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile, "w")) as db:
                    db[key] = uri
            except dbm.error as e:
                raise NamingError("dbm error in setitem: " + str(e))

    def __len__(self):
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile)) as db:
                    return len(db)
            except dbm.error as e:
                raise NamingError("dbm error in len: " + str(e))

    def __contains__(self, item):
        item = item.encode("utf-8")
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile)) as db:
                    return item in db
            except dbm.error as e:
                raise NamingError("dbm error in contains: " + str(e))

    def __delitem__(self, key):
        key = key.encode("utf-8")
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile, "w")) as db:
                    del db[key]
            except dbm.error as e:
                raise NamingError("dbm error in delitem: " + str(e))

    def __iter__(self):
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile)) as db:
                    return iter([key.decode("utf-8") for key in db.keys()])
            except dbm.error as e:
                raise NamingError("dbm error in iter: " + str(e))

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
                raise NamingError("dbm error in clear: " + str(e))

    def optimized_prefix_list(self, prefix, return_metadata=False):
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile)) as db:
                    result = {}
                    if hasattr(db, "items"):
                        for key, value in db.items():
                            key = key.decode("utf-8")
                            if key.startswith(prefix):
                                uri = value.decode("utf-8")
                                result[key] = (uri, frozenset()) if return_metadata else uri    # always return empty metadata
                    else:
                        for key in db.keys():
                            keystr = key.decode("utf-8")
                            if keystr.startswith(prefix):
                                uri = db[key].decode("utf-8")
                                result[keystr] = (uri, frozenset()) if return_metadata else uri     # always return empty metadata
                    return result
            except dbm.error as e:
                raise NamingError("dbm error in optimized_prefix_list: " + str(e))

    def optimized_regex_list(self, regex, return_metadata=False):
        try:
            regex = re.compile(regex + "$")  # add end of string marker
        except re.error as x:
            raise NamingError("invalid regex: " + str(x))
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile)) as db:
                    result = {}
                    if hasattr(db, "items"):
                        for key, value in db.items():
                            key = key.decode("utf-8")
                            if regex.match(key):
                                uri = value.decode("utf-8")
                                result[key] = (uri, frozenset()) if return_metadata else uri     # always return empty metadata
                    else:
                        for key in db.keys():
                            keystr = key.decode("utf-8")
                            if regex.match(keystr):
                                uri = db[key].decode("utf-8")
                                result[keystr] = (uri, frozenset()) if return_metadata else uri    # always return empty metadata
                    return result
            except dbm.error as e:
                raise NamingError("dbm error in optimized_regex_list: " + str(e))

    def optimized_metadata_search(self, metadata_all=None, metadata_any=None, return_metadata=False):
        if metadata_all or metadata_any:
            raise NamingError("DbmStorage doesn't support metadata")
        return self.everything(return_metadata)

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
                raise NamingError("dbm error in remove_items: " + str(e))

    def everything(self, return_metadata=False):
        with self.lock:
            try:
                with closing(dbm.open(self.dbmfile)) as db:
                    result = {}
                    if hasattr(db, "items"):
                        for key, value in db.items():
                            uri = value.decode("utf-8")
                            result[key.decode("utf-8")] = (uri, frozenset()) if return_metadata else uri    # always return empty metadata
                    else:
                        for key in db.keys():
                            uri = db[key].decode("utf-8")
                            result[key.decode("utf-8")] = (uri, frozenset()) if return_metadata else uri    # always return empty metadata
                    return result
            except dbm.error as e:
                raise NamingError("dbm error in everything: " + str(e))

    def close(self):
        pass
