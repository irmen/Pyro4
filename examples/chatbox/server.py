from __future__ import with_statement
import sys
import Pyro4

# Chat box administration server.
# Handles logins, logouts, channels and nicknames, and the chatting.
class ChatBox(object):
    def __init__(self):
        self.channels={}        # registered channels { channel --> (nick, client callback) list }
        self.nicks=[]            # all registered nicks on this server
    def getChannels(self):
        return self.channels.keys()
    def getNicks(self):
        return self.nicks
    def join(self, channel, nick, callback):
        if nick in self.nicks:
            raise ValueError('this nick is already in use')
        if channel not in self.channels:
            print 'CREATING NEW CHANNEL',channel
            self.channels[channel]=[]
        self.channels[channel].append((nick,callback))
        self.nicks.append(nick)
        callback._pyroOneway.add('message')    # don't wait for results for this method
        print nick,'JOINED',channel
        self.publish(channel,'SERVER','** '+nick+' joined **')
        return [nick for (nick,c) in self.channels[channel]]  # return all nicks in this channel
    def leave(self,channel,nick):
        if not channel in self.channels:
            print 'IGNORED UNKNOWN CHANNEL',channel
            return
        for (n,c) in self.channels[channel]:
            if n==nick:
                self.channels[channel].remove((n,c))
                break
        self.publish(channel,'SERVER','** '+nick+' left **')
        if len(self.channels[channel])<1:
            del self.channels[channel]
            print 'REMOVED CHANNEL',channel
        self.nicks.remove(nick)
        print nick,'LEFT',channel
    def publish(self, channel, nick, msg):
        if not channel in self.channels:
            print 'IGNORED UNKNOWN CHANNEL',channel
            return
        for (n,c) in self.channels[channel][:]:        # use a copy of the list
            try:
                c.message(nick,msg)    # oneway call
            except Pyro4.errors.ConnectionClosedError,x:
                # connection dropped, remove the listener if it's still there
                # check for existence because other thread may have killed it already
                if (n,c) in self.channels[channel]:
                    self.channels[channel].remove((n,c))
                    print 'Removed dead listener',n,c

with Pyro4.core.Daemon() as daemon:
    with Pyro4.naming.locateNS() as ns:
        uri=daemon.register(ChatBox())
        ns.remove("example.chatbox.server")
        ns.register("example.chatbox.server",uri)
    # enter the service loop.
    print 'Chatbox open.'
    daemon.requestLoop()
