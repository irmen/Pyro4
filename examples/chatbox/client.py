from __future__ import with_statement
import Pyro4
from Pyro4 import threadutil

# The daemon is running in its own thread, to be able to deal with server
# callback messages while the main thread is processing user input. 

class Chatter(object):
    def __init__(self):
        self.chatbox = Pyro4.core.Proxy('PYRONAME:example.chatbox.server')
        self.abort=0
    def message(self, nick, msg):
        if nick!=self.nick:
            print '['+nick+'] '+msg
    def start(self):
        nicks=self.chatbox.getNicks()
        if nicks:
            print 'The following people are on the server: ',', '.join(nicks)
        channels=sorted(self.chatbox.getChannels())
        if channels:
            print 'The following channels already exist: ',', '.join(channels)
            print
            self.channel=raw_input('Choose a channel or create a new one: ')
        else:
            print 'The server has no active channels.'
            self.channel=raw_input('Name for new channel: ')
        self.nick=raw_input('Choose a nickname: ')
        proxy=Pyro4.core.Proxy(self._pyroDaemon.uriFor(self))
        people=self.chatbox.join(self.channel,self.nick,proxy)
        print 'Joined channel',self.channel,'as',self.nick
        print 'People on this channel:',', '.join(people)
        print 'Ready for input! Type /quit to quit'
        try:
            try:
                while not self.abort:
                    line=raw_input('> ')
                    if line=='/quit':
                        break
                    if line:
                        self.chatbox.publish(self.channel,self.nick,line)
            except EOFError:
                pass
        finally:
            self.chatbox.leave(self.channel, self.nick)
            self.abort=1
            self._pyroDaemon.shutdown()

class DaemonThread(threadutil.Thread):
    def __init__(self, chatter):
        threadutil.Thread.__init__(self)
        self.chatter=chatter
        self.setDaemon(True)
    def run(self):
        with Pyro4.core.Daemon() as daemon:
            daemon.register(self.chatter)
            daemon.requestLoop(lambda: not self.chatter.abort)

chatter=Chatter()
daemonthread=DaemonThread(chatter)
daemonthread.start()
chatter.start()
print 'Exiting.'
