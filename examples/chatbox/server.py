from __future__ import with_statement
import Pyro4

# Chat box administration server.
# Handles logins, logouts, channels and nicknames, and the chatting.
class ChatBox(object):
    def __init__(self):
        self.channels={}        # registered channels { channel --> (nick, client callback) list }
        self.nicks=[]            # all registered nicks on this server
    def getChannels(self):
        return list(self.channels.keys())
    def getNicks(self):
        return self.nicks
    def join(self, channel, nick, callback):
        if not channel or not nick:
            raise ValueError("invalid channel or nick name")
        if nick in self.nicks:
            raise ValueError('this nick is already in use')
        if channel not in self.channels:
            print('CREATING NEW CHANNEL %s' % channel)
            self.channels[channel]=[]
        self.channels[channel].append((nick, callback))
        self.nicks.append(nick)
        callback._pyroOneway.add('message')    # don't wait for results for this method
        print("%s JOINED %s" % (nick, channel))
        self.publish(channel,'SERVER','** '+nick+' joined **')
        return [nick for (nick,c) in self.channels[channel]]  # return all nicks in this channel
    def leave(self,channel,nick):
        if not channel in self.channels:
            print('IGNORED UNKNOWN CHANNEL %s' % channel)
            return
        for (n,c) in self.channels[channel]:
            if n==nick:
                self.channels[channel].remove((n, c))
                break
        self.publish(channel,'SERVER','** '+nick+' left **')
        if len(self.channels[channel])<1:
            del self.channels[channel]
            print('REMOVED CHANNEL %s' % channel)
        self.nicks.remove(nick)
        print("%s LEFT %s" % (nick, channel))
    def publish(self, channel, nick, msg):
        if not channel in self.channels:
            print('IGNORED UNKNOWN CHANNEL %s' % channel)
            return
        for (n,c) in self.channels[channel][:]:        # use a copy of the list
            try:
                c.message(nick,msg)    # oneway call
            except Pyro4.errors.ConnectionClosedError:
                # connection dropped, remove the listener if it's still there
                # check for existence because other thread may have killed it already
                if (n,c) in self.channels[channel]:
                    self.channels[channel].remove((n, c))
                    print('Removed dead listener %s %s' % (n, c))

with Pyro4.core.Daemon() as daemon:
    with Pyro4.naming.locateNS() as ns:
        uri=daemon.register(ChatBox())
        ns.register("example.chatbox.server",uri)
    # enter the service loop.
    print('Chatbox open.')
    daemon.requestLoop()
