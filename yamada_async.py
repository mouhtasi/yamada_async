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
            msg = token[3]
            nick, user, host = self.split_netmask(src)
            if dest == self.nick and '\x01PING' in msg:
                if len(token) >= 5:
                    self.notice(nick, '\x01PING %s\x01' % token[4][:-1])
                else:
                    self.notice(nick, '\x01PING\x01')
        elif src == 'PING':
            self.send_data('PONG %s' % token[1])
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

if __name__ == '__main__':
    from asyncore import loop
    host, port = 'irc.rizon.net', 6667
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
