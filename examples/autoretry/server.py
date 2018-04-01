import Pyro4


@Pyro4.expose
class CalcServer(object):
    def add(self, num1, num2):
        print("calling add: %d, %d" % (num1, num2))
        return num1 + num2


Pyro4.config.COMMTIMEOUT = 0.5  # the server should time out easily now

Pyro4.core.Daemon.serveSimple({
    CalcServer: "example.autoretry"
})
