from __future__ import print_function
import Pyro4
import Pyro4.constants


secret_code = "pancakes"


class CustomDaemon(Pyro4.Daemon):
    def validateHandshake(self, conn, data):
        print("Daemon received handshake request from:", conn.sock.getpeername())
        print("Handshake data:", data)
        # if needed, you can inspect Pyro4.current_context
        if data == secret_code:
            print("Secret code okay! Connection accepted.")
            # return some custom handshake data:
            return ["how", "are", "you", "doing"]
        else:
            print("Secret code wrong! Connection refused.")
            raise ValueError("wrong secret code, connection refused")

    def clientDisconnect(self, conn):
        print("Daemon client disconnects:", conn.sock.getpeername())


daemon = CustomDaemon()
print("Server is ready. You can use the following URI to connect:")
print(daemon.uriFor(Pyro4.constants.DAEMON_NAME))
print("When asked, enter the following secret code: ", secret_code)
daemon.requestLoop()
