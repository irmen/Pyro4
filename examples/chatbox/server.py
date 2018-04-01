import Pyro4


# Chat box administration server.
# Handles logins, logouts, channels and nicknames, and the chatting.
@Pyro4.expose
@Pyro4.behavior(instance_mode="single")
class ChatBox(object):
    def __init__(self):
        self.channels = {}  # registered channels { channel --> (nick, client callback) list }
        self.nicks = []  # all registered nicks on this server

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
            self.channels[channel] = []
        self.channels[channel].append((nick, callback))
        self.nicks.append(nick)
        print("%s JOINED %s" % (nick, channel))
        self.publish(channel, 'SERVER', '** ' + nick + ' joined **')
        return [nick for (nick, c) in self.channels[channel]]  # return all nicks in this channel

    def leave(self, channel, nick):
        if channel not in self.channels:
            print('IGNORED UNKNOWN CHANNEL %s' % channel)
            return
        for (n, c) in self.channels[channel]:
            if n == nick:
                self.channels[channel].remove((n, c))
                break
        self.publish(channel, 'SERVER', '** ' + nick + ' left **')
        if len(self.channels[channel]) < 1:
            del self.channels[channel]
            print('REMOVED CHANNEL %s' % channel)
        self.nicks.remove(nick)
        print("%s LEFT %s" % (nick, channel))

    def publish(self, channel, nick, msg):
        if channel not in self.channels:
            print('IGNORED UNKNOWN CHANNEL %s' % channel)
            return
        for (n, c) in self.channels[channel][:]:  # use a copy of the list
            try:
                c.message(nick, msg)  # oneway call
            except Pyro4.errors.ConnectionClosedError:
                # connection dropped, remove the listener if it's still there
                # check for existence because other thread may have killed it already
                if (n, c) in self.channels[channel]:
                    self.channels[channel].remove((n, c))
                    print('Removed dead listener %s %s' % (n, c))


Pyro4.Daemon.serveSimple({
    ChatBox: "example.chatbox.server"
})
