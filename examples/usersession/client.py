from __future__ import print_function
import threading
import time
import sys
import Pyro4


if sys.version_info < (3, 0):
    input = raw_input


def get_user_token():
    return "user123"


class CustomAnnotationProxy(Pyro4.Proxy):
    # override the method that adds annotations and add our own custom user token annotation
    def _pyroAnnotations(self):
        return {"USER": get_user_token().encode("utf-8")}


class DbAccessor(threading.Thread):
    def __init__(self, uri):
        super(DbAccessor, self).__init__()
        self.proxy = CustomAnnotationProxy(uri)
        self.daemon = True

    def run(self):
        for i in range(3):
            try:
                self.proxy.store("number", 100+i)
                num = self.proxy.retrieve("number")
                print("[%s] num=%s" % (self.name, num))
            except Exception:
                import traceback
                traceback.print_exc()


print("\n***** Sequential access using multiple proxies on the Session-Bound Database... (no issues)")
with CustomAnnotationProxy("PYRONAME:example.usersession.sessiondb") as p1,\
        CustomAnnotationProxy("PYRONAME:example.usersession.sessiondb") as p2:
    p1.store("number", 42)
    p1.retrieve("number")
    p2.store("number", 43)
    p2.retrieve("number")

print("\n***** Sequential access using multiple proxies on the Singleton Database... (no issues)")
with CustomAnnotationProxy("PYRONAME:example.usersession.singletondb") as p1,\
        CustomAnnotationProxy("PYRONAME:example.usersession.singletondb") as p2:
    p1.store("number", 42)
    p1.retrieve("number")
    p2.store("number", 43)
    p2.retrieve("number")

print("\n***** Multiple concurrent proxies on the Session-Bound Database... (no issues)")
input("enter to start: ")
t1 = DbAccessor("PYRONAME:example.usersession.sessiondb")
t2 = DbAccessor("PYRONAME:example.usersession.sessiondb")
t1.start()
t2.start()
time.sleep(1)
t1.join()
t2.join()

print("\n***** Multiple concurrent proxies on the Singleton Database... (threading problem)")
input("enter to start: ")
t1 = DbAccessor("PYRONAME:example.usersession.singletondb")
t2 = DbAccessor("PYRONAME:example.usersession.singletondb")
t1.start()
t2.start()
time.sleep(1)
t1.join()
t2.join()
