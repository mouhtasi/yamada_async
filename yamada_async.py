from asynchat import async_chat
from socket import AF_INET, SOCK_STREAM
import time

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
        self.topic_req = ('', False)
        self.recieved_data = ''
        self.create_socket(AF_INET, SOCK_STREAM)
        self.connect((host, port))

    def connection_made(self):
        '''Actions to take when a connection is made with the server.'''
        self.send_data('MODE %s +iB' % self.nick)  # set user mode invisible and bot
        for channel in self.channels:
            self.send_data('JOIN #%s' % channel)

    def send_data(self, data):
        '''Send data to the server.'''
        print '%s << %s' % (self.timestamp(), data)
        data += '\r\n'
        self.push(data)

    def handle_connect(self):
        '''Actions to take when creating the connection.'''
        self.send_data('NICK :%s' % nick)
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
                if dest == self.nick and nick == 'gesshoki':
                    self.owner_triggers(dest, msg)
                else:
                    self.triggers(dest, msg)

        elif src == 'PING':
            self.send_data('PONG %s' % token[1])
        elif code == '332' and self.topic_req[1]:
            msg = token[4].lstrip(':')
            ctr = 5
            while ctr < len(token):
                msg += ' ' + token[ctr]
                ctr += 1
            self.send_topic(self.topic_req[0], msg)
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

    def msg(self, user, data):
        '''Send a message to a user.'''
        self.send_data('PRIVMSG %s :%s' % (user, data))

    def notice(self, dest, msg):
        '''Send a notice to a user.'''
        self.send_data('NOTICE %s :%s' % (dest, msg))

    def action(self, dest, msg):
        '''Do an action in a channel.'''
        self.msg(dest, '\x01ACTION %s\x01' % msg)

    def request_topic(self, chan):
        '''Request the topic of chan.'''
        self.send_data('TOPIC %s' % chan)
        self.topic_req = (chan, True)

    def send_topic(self, chan, topic):
        '''Print the topic of chan.'''
        self.msg(chan, 'Topic for %s is: %s' % (chan, topic))
        self.topic_req = ('', False)

    def triggers(self, dest, message):
        '''Actions to perform when a trigger is triggered.'''
        trigger, sep, msg = message.partition(' ')

        if trigger == '!echo':
            self.msg(dest, msg)
        elif trigger == '!topic':
            self.request_topic(dest)

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

if __name__ == '__main__':
    from asyncore import loop
    host, port = 'irc.rizon.net', 6667
    owner = 'botowner'
    nick = 'Yamadabot'
    username = 'Yamada'
    channels = ['yamada_test']
    client = IRCClient(host, port, nick, username, channels)
    try:
        loop(timeout=1)
    except KeyboardInterrupt:
        print 'Terminated from console.'
    except:
        print 'Terminated due to fatal error.'
