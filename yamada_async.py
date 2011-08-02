from asynchat import async_chat
from socket import AF_INET, SOCK_STREAM
import time
import logger
import yaml

class IRCClient(async_chat):
    terminator = '\r\n'
    ctcp_version = None

    def __init__(self, host, port, nick, user, channels):
        async_chat.__init__(self)
        self.host = host
        self.port = port
        self.nick = nick
        self.user = user
        self.channels = [] if (channels is None) else channels
        self.topics = {}
        self.recieved_data = ''
        self.create_socket(AF_INET, SOCK_STREAM)
        self.connect((host, port))

    def connection_made(self):
        '''Actions to take when a connection is made with the server.'''
        self.send_data('MODE %s +iB' % self.nick)  # user mode invisible and bot
        log.log('Connected to %s as %s.' % (self.host, self.nick))
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
            msg = token[3].lstrip(':')
            ctr = 4
            while ctr < len(token):
                msg += ' ' + token[ctr]
                ctr += 1

            nick, user, host = self.split_netmask(src)
            if dest == self.nick and '\x01PING' in msg:
                if len(token) >= 5:
                    self.notice(nick, msg)
                else:
                    self.notice(nick, '\x01PING\x01')

            elif msg[0] == '!':
                if dest == self.nick and nick == owner:
                    self.owner_triggers(dest, msg)
                else:
                    self.triggers(dest, msg)

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

    def split_netmask(self, netmask):
        '''Extract information from the netmask.'''
        nick = netmask.split('!')[0].lstrip(':')
        user = netmask.split('@')[0].split('!')[1]
        host = netmask.split('@')[1]
        return (nick, user, host)

    def join(self, channel):
        if channel[0] != '#':
            channel = '#%s' % channel
        self.send_data('JOIN %s' % channel)
        log.log('Joined %s.' % channel)

    def part(self, channel, reason):
        if channel[0] != '#':
            channel = '#%s' % channel
        self.send_data('PART %s :%s' % (channel, reason))
        log.log('Left %s. Reason: %s' % (channel, reason))

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

            self.msg(chan, 'Topic for %s is: "%s" set by %s on %s' % (chan, topic,
                                                                      by, time_ch))

    def triggers(self, dest, message):
        '''Actions to perform when a trigger is triggered.'''
        trigger, sep, msg = message.partition(' ')

        if trigger == '!echo':
            self.msg(dest, msg)
        elif trigger == '!topic':
            self.send_topic(dest)

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

if __name__ == '__main__':
    from asyncore import loop
    conf = open('config.yaml', 'r')
    config = yaml.load(conf)
    conf.close()
    owner = config['owner']
    client = IRCClient(config['host'], config['port'], config['nick'],
                       config['username'], config['channels'])
    logfile = config['logfile']

    try:
        global log
        log = logger.Logger(logfile)
        loop(timeout=1)
    except KeyboardInterrupt:
        log.close_log('Terminated by user.')
        print 'Terminated by user.'
    except:
        log.close_log('Fatal error.')
        print 'Terminated due to fatal error.'
