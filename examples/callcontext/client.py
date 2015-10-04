from __future__ import print_function
import sys
import Pyro4
import uuid

# example: set a single correlation id on the context that should be passed along
Pyro4.current_context.correlation_id = uuid.uuid1()
print("correlation id set to:", Pyro4.current_context.correlation_id)

if sys.version_info < (3, 0):
    input = raw_input


class CustomAnnotationProxy(Pyro4.Proxy):
    def __init__(self, uri):
        super(CustomAnnotationProxy, self).__init__(uri)
        self._pyroHmacKey = b"secr3t_k3y"

    # override the method that adds annotations and add our own,
    # but be sure to call the base class method.
    def _pyroAnnotations(self):
        annotations = super(CustomAnnotationProxy, self)._pyroAnnotations()
        annotations["XYZZ"] = b"Hello, I am a custom annotation from the proxy!"
        return annotations

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
    # async
    print("Async proxy message...")
    asyncproxy = Pyro4.async(proxy)
    result = asyncproxy.echo("hello-ASYNC")
    _ = result.value

    # oneway
    print("Finally, sending a oneway message...")
    proxy.oneway("hello-ONEWAY")

print("See the console output on the server for more results.")
