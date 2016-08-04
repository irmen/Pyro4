from __future__ import print_function
import Pyro4


@Pyro4.behavior(instance_mode="single")
class SingleInstance(object):
    @Pyro4.expose
    def msg(self, message):
        print("[%s] %s.msg: %s" % (id(self), self.__class__.__name__, message))
        return id(self)


@Pyro4.behavior(instance_mode="session", instance_creator=lambda clazz: clazz.create_instance())
class SessionInstance(object):
    @Pyro4.expose
    def msg(self, message):
        print("[%s] %s.msg: %s" % (id(self), self.__class__.__name__, message))
        return id(self), self.correlation_id
    @classmethod
    def create_instance(cls):
        obj = cls()
        obj.correlation_id = Pyro4.current_context.correlation_id
        return obj


@Pyro4.behavior(instance_mode="percall")
class PercallInstance(object):
    @Pyro4.expose
    def msg(self, message):
        print("[%s] %s.msg: %s" % (id(self), self.__class__.__name__, message))
        return id(self)


if __name__ == "__main__":
    # please make sure a name server is running somewhere first.
    Pyro4.Daemon.serveSimple({
        SingleInstance: "instance.single",
        SessionInstance: "instance.session",
        PercallInstance: "instance.percall"
    }, verbose=True)
