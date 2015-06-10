from __future__ import print_function
import sys
import Pyro4

if sys.version_info < (3, 0):
    input = raw_input


class CustomHandshakeProxy(Pyro4.Proxy):
    def _pyroHandshake(self):
        print("Proxy sending handshake data... (secret code: "+self._pyroStuff["secret_code"]+")")
        return self._pyroStuff["secret_code"]

    def _pyroHandshakeResponse(self, response):
        # this will get called if the connection is okay
        print("Proxy received handshake response data: ", response)


uri = input("Enter the URI of the server object: ")
secret = input("Enter the secret code of the server (or make a mistake on purpose to see what happens): ")
with CustomHandshakeProxy(uri) as proxy:
    proxy._pyroStuff = {"secret_code": secret}
    print("connecting...")
    proxy._pyroBind()
    proxy.ping()
    print("Connection ok!")

print("done.")
