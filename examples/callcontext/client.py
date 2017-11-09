from __future__ import print_function
import sys
import Pyro4
import uuid

# example: set a single correlation id on the context that should be passed along
Pyro4.current_context.correlation_id = uuid.uuid4()
print("correlation id set to:", Pyro4.current_context.correlation_id)

if sys.version_info < (3, 0):
    input = raw_input


# custom proxy needed to get to annotation data, before Pyro 4.56
class CustomAnnotationProxy(Pyro4.Proxy):
    def __init__(self, uri):
        super(CustomAnnotationProxy, self).__init__(uri)
        self._pyroHmacKey = b"secr3t_k3y"

    # override the method that adds annotations and add our own
    def _pyroAnnotations(self):
        return {"XYZZ": b"Hello, I am a custom annotation from the proxy!"}

    def _pyroResponseAnnotations(self, annotations, msgtype):
        print("    Got response (msgtype=%d). Annotations:" % msgtype)
        for key in annotations:
            if key == "CORR":
                value = uuid.UUID(bytes=annotations[key])
            elif key == "HMAC":
                value = "[...]"
            else:
                value = annotations[key]
            print("      {0} -> {1}".format(key, value))


uri = input("Enter the URI of the server object: ")

print("\n------- (older) method to get annotations via callback on custom proxy... -----\n")
with CustomAnnotationProxy(uri) as proxy:
    print("Sending a few messages using one proxy...")
    for i in range(4):
        msg = proxy.echo("hello-%d" % i)

proxies = [CustomAnnotationProxy(uri) for _ in range(5)]
for p in proxies:
    print("Sending one message from new proxy...")
    msg = p.echo("hello-%d" % id(p))
    p._pyroRelease()

with CustomAnnotationProxy(uri) as proxy:
    # oneway
    print("Sending a oneway message... (should only print a connection ok response)")
    proxy.oneway("hello-ONEWAY-1")
    print("Sending another oneway message... (should not print a response at all)")
    proxy.oneway("hello-ONEWAY-2")
    # asynchronous
    print("Asynchronous proxy message...")
    proxy._pyroAsync()
    result = proxy.echo("hello-ASYNC")
    _ = result.value


print("\n------- get annotations via normal proxy and the call context... -----\n")
input("press enter:")
# the code below works as of Pyro 4.56.
with Pyro4.Proxy(uri) as proxy:
    proxy._pyroHmacKey = b"secr3t_k3y"
    print("normal call")

    Pyro4.current_context.annotations = {"XYZZ": b"custom annotation from client via new way(1)"}
    result = proxy.echo("hi there - new method of annotation access in client")
    print("Annotations in response were: ", Pyro4.current_context.response_annotations)

    print("\noneway call")
    Pyro4.current_context.annotations = {"XYZZ": b"custom annotation from client via new way(2)"}
    proxy.oneway("hi there ONEWAY - new method of annotation access in client")
    print("Annotations in response were: ", Pyro4.current_context.response_annotations)
    print("   (should be empty because oneway!)")


print("\nSee the console output on the server for more results.")
