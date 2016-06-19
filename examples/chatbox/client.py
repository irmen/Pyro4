import sys
import Pyro4
from Pyro4 import threadutil


if sys.version_info < (3, 0):
    input = raw_input


# The daemon is running in its own thread, to be able to deal with server
# callback messages while the main thread is processing user input.

class Chatter(object):
    def __init__(self):
        self.chatbox = Pyro4.core.Proxy('PYRONAME:example.chatbox.server')
        self.abort = 0

    @Pyro4.expose
    @Pyro4.oneway
    def message(self, nick, msg):
        if nick != self.nick:
            print('[{0}] {1}'.format(nick, msg))

    def start(self):
        nicks = self.chatbox.getNicks()
        if nicks:
            print('The following people are on the server: %s' % (', '.join(nicks)))
        channels = sorted(self.chatbox.getChannels())
        if channels:
            print('The following channels already exist: %s' % (', '.join(channels)))
            self.channel = input('Choose a channel or create a new one: ').strip()
        else:
            print('The server has no active channels.')
            self.channel = input('Name for new channel: ').strip()
        self.nick = input('Choose a nickname: ').strip()
        people = self.chatbox.join(self.channel, self.nick, self)
        print('Joined channel %s as %s' % (self.channel, self.nick))
        print('People on this channel: %s' % (', '.join(people)))
        print('Ready for input! Type /quit to quit')
        try:
            try:
                while not self.abort:
                    line = input('> ').strip()
                    if line == '/quit':
                        break
                    if line:
                        self.chatbox.publish(self.channel, self.nick, line)
            except EOFError:
                pass
        finally:
            self.chatbox.leave(self.channel, self.nick)
            self.abort = 1
            self._pyroDaemon.shutdown()


class DaemonThread(threadutil.Thread):
    def __init__(self, chatter):
        threadutil.Thread.__init__(self)
        self.chatter = chatter
        self.setDaemon(True)

    def run(self):
        with Pyro4.core.Daemon() as daemon:
            daemon.register(self.chatter)
            daemon.requestLoop(lambda: not self.chatter.abort)


chatter = Chatter()
daemonthread = DaemonThread(chatter)
daemonthread.start()
chatter.start()
print('Exit.')
