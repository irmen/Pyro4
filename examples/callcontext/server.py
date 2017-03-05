from __future__ import print_function
import Pyro4
import threading


@Pyro4.expose
class EchoServer(object):
    def echo(self, message):
        ctx = Pyro4.current_context
        print("\nGot Message:", message)
        print("  thread: ", threading.current_thread().ident)
        print("  obj.pyroid: ", self._pyroId)
        print("  obj.daemon: ", self._pyroDaemon)
        print("  context.client: ", ctx.client)
        print("  context.client_sock_addr: ", ctx.client_sock_addr)
        print("  context.seq: ", ctx.seq)
        print("  context.msg_flags: ", ctx.msg_flags)
        print("  context.serializer_id: ", ctx.serializer_id)
        print("  context.correlation_id:", ctx.correlation_id)
        if "XYZZ" in ctx.annotations:
            print("  custom annotation 'XYZZ':", ctx.annotations["XYZZ"])
        return message

    @Pyro4.oneway
    def oneway(self, message):
        return self.echo(message)


class CustomDaemon(Pyro4.Daemon):
    def annotations(self):
        return {"DDAA": b"custom response annotation set by the daemon"}


with CustomDaemon() as daemon:
    daemon._pyroHmacKey = b"secr3t_k3y"
    uri = daemon.register(EchoServer, "example.context")  # provide a logical name ourselves
    print("Server is ready. You can use the following URI to connect:")
    print(uri)
    daemon.requestLoop()
