from asynchat import async_chat
from socket import AF_INET, SOCK_STREAM
import time
import math
import os
try:
    import cPickle as pickle
except:
    import pickle

class IRCClient(async_chat):
    terminator = '\r\n'
    ctcp_version = None

    def __init__(self, host, port, nick, user, nick_pass, channels, log):
        async_chat.__init__(self)
        self.host = host
        self.port = port
        self.nick = nick
        self.user = user
        self.nick_pass = nick_pass
        self.channels = [] if (channels is None) else channels
        self.topics = {}
        self.recieved_data = ''
        self.create_socket(AF_INET, SOCK_STREAM)
        self.connect((host, port))
        self.log = log
        self.seen = {}
        self.seen_pkl = 'seen.pkl'
        self.load_seen()

    def connection_made(self):
        '''Actions to take when a connection is made with the server.'''
        self.send_data('MODE %s +iB' % self.nick)  # user mode invisible & bot
        if self.nick_pass != '':
            self.identify(self.nick_pass)
        self.log.log('Connected to %s as %s.' % (self.host, self.nick))
        for channel in self.channels:
            self.join(channel)

    def send_data(self, data):
        '''Send data to the server.'''
        print '%s << %s' % (self.timestamp(), data)
        data += '\r\n'
        self.push(data)

    def handle_connect(self):
        '''Actions to take when creating the connection.'''
        self.send_data('NICK :%s' % self.nick)
        self.send_data('USER %s 0 %s :%s' % (self.user, self.user, self.user))

    def handle_data(self, data):
        '''Actions to take with recieved data.'''
        print '%s >> %s' % (self.timestamp(), data)
        token = data.split()
        src = token[0]
        code = token[1]

        if code == 'PRIVMSG':
            dest = token[2]
            msg = token[3][1::]
            ctr = 4
            while ctr < len(token):
                msg += ' ' + token[ctr]
                ctr += 1

            nick, user, host = self.split_netmask(src)
	    if dest != self.nick:
		self.add_seen(nick, dest, msg)

            if dest == self.nick and '\x01PING' in msg:
                if len(token) >= 5:
                    self.notice(nick, msg)
                else:
                    self.notice(nick, '\x01PING\x01')

            elif msg[0] == '!':
                if dest == self.nick and nick == owner:
                    self.owner_triggers(dest, msg)
                else:
                    self.triggers(nick, dest, msg)

        elif code == 'TOPIC':
            chan = token[2]
            topic = token[3].lstrip(':')
            ctr = 4
            while ctr < len(token):
                topic += ' ' + token[ctr]
                ctr += 1

            nick, _, _ = self.split_netmask(src)
            self.topic_change(chan, topic, nick)

        elif src == 'PING':
            self.send_data('PONG %s' % token[1])
        elif code == '332':
            topic = token[4].lstrip(':')
            ctr = 5
            while ctr < len(token):
                topic += ' ' + token[ctr]
                ctr += 1
            self.topics[token[3]] = [topic, '', '']
        elif code == '333':
            by = token[4]
            time = token[5]

            self.topics[token[3]][1] = by
            self.topics[token[3]][2] = time

        elif code == '376' or code == '422': # end of MOTD or MOTD not found
            self.connection_made()

    def found_terminator(self):
        self.handle_data(self.recieved_data)
        self.recieved_data = ''

    def collect_incoming_data(self, data):
        self.recieved_data += data

    def timestamp(self):
        return time.strftime('%H:%M:%S', time.localtime(time.time()))

    def load_seen(self):
        if os.path.isfile(self.seen_pkl):
            pkl = open(self.seen_pkl, 'rb')
            self.seen = pickle.load(pkl)
            pkl.close()

    def add_seen(self, nick, dest, msg):
        self.seen[nick] = [time.time(), dest, msg]

    def save_seen(self):
        pkl = open(self.seen_pkl, 'wb')
        pickle.dump(self.seen, pkl)
        pkl.close()

    def split_netmask(self, netmask):
        '''Extract information from the netmask.'''
        nick = netmask.split('!')[0].lstrip(':')
        user = netmask.split('@')[0].split('!')[1]
        host = netmask.split('@')[1]
        return (nick, user, host)

    def identify(self, nick_pass):
        self.msg('nickserv', 'identify %s' % nick_pass)

    def join(self, channel):
        if channel[0] != '#':
            channel = '#%s' % channel
        self.send_data('JOIN %s' % channel)
        self.log.log('Joined %s.' % channel)

    def part(self, channel, reason):
        if channel[0] != '#':
            channel = '#%s' % channel
        self.send_data('PART %s :%s' % (channel, reason))
        self.log.log('Left %s. Reason: %s' % (channel, reason))

    def msg(self, user, data):
        '''Send a message to a user.'''
        self.send_data('PRIVMSG %s :%s' % (user, data))

    def notice(self, dest, msg):
        '''Send a notice to a user.'''
        self.send_data('NOTICE %s :%s' % (dest, msg))

    def action(self, dest, msg):
        '''Do an action in a channel.'''
        self.msg(dest, '\x01ACTION %s\x01' % msg)

    def topic_change(self, chan, topic, by):
        '''Update self.topics to new topic.'''
        t = time.ctime(time.time())
        self.topics[chan] = [topic, by, t]

    def send_topic(self, chan):
        '''Print the topic of chan.'''
        if chan in self.topics:
            topic, by, time_ch = self.topics[chan]

            if '!' in by:
                by, user, host = self.split_netmask(by)

            if ':' not in time_ch:
                time_ch = time.ctime(int(time_ch))

            self.msg(chan, 'Topic for %s is: "%s" set by %s on %s' % (chan,
	                                                    topic, by, time_ch))

    def triggers(self, nick, dest, message):
        '''Actions to perform when a trigger is triggered.'''
        trigger, sep, msg = message.partition(' ')

        if trigger == '!echo':
            self.msg(dest, msg)
        elif trigger == '!topic':
            self.send_topic(dest)
        elif trigger == '!seen':
            now = time.time()
            who, _, _ = msg.partition(' ')
	    if msg != '':
		if who in self.seen.keys():
		    then, chan, said = self.seen[who]
		    delta = time.time() - then
		    seen = ('%s, %s was last seen in %s %s ago saying: %s' % (nick, who, chan, self.time_ago(delta), said))
		    self.msg(dest, seen)
		else:
		    self.msg(dest, 'I have not seen %s before.' % who)

    def owner_triggers(self, dest, message):
        '''Triggers which are only triggered in PM from bot owner.'''
        trigger, sep, text = message.partition(' ')

        if trigger == '!raw':
            self.send_data(text)

        else:
            dest, sep, msg = text.partition(' ')
            if trigger == '!say':
                #!say <nick/channel> <text>
                self.msg(dest, msg)
            elif trigger == '!do':
                #!do <nick/channel> <text>
                self.action(dest, msg)
            elif trigger == '!join':
                self.join(dest)
            elif trigger == '!part':
                self.part(dest, msg)

    def time_ago(self, diff):
        stime = ''
        if diff <= 60:
            return '%s %s' % (str(int(diff)), 'second' if diff is 1 else 'seconds')

        else:
            if (diff / 604800) >= 1:
                factor = int(math.floor(diff / 604800))
                diff -= 604800 * factor
                stime = '%s %s ' % (factor, 'week' if factor is 1 else 'weeks')
            if diff > 0:
                if (diff / 86400) >= 1:
                    factor = int(math.floor(diff / 86400))
                    diff -= 86400 * factor
                    stime += '%s %s ' % (factor, 'day' if factor is 1 else
                                         'days')
            if diff > 0:
                if (diff / 3600) >= 1:
                    factor = int(math.floor(diff / 3600))
                    diff -= 3600 * factor
                    stime += '%s %s ' % (factor, 'hour' if factor is 1 else
                                         'hours')
            if diff > 0:
                if (diff / 60) >= 1:
                    factor = int(math.floor(diff / 60))
                    diff -= 60 * factor
                    stime += '%s %s ' % (factor, 'minute' if factor is 1 else
		                         'minutes')
            if diff > 0:
                stime += '%s seconds' % factor
        return stime