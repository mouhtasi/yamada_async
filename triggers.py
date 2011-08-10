import time
import math

def triggers(IRCClient, nick, dest, message):
    '''Actions to perform when a trigger is triggered.'''
    trigger, sep, msg = message.partition(' ')
    if trigger == '!echo':
        IRCClient.msg(dest, msg)
    elif trigger == '!topic':
        send_topic(IRCClient, dest)
    elif trigger == '!seen':
        now = time.time()
        who, _, _ = msg.partition(' ')
        if msg != '':
            if who in IRCClient.seen.keys():
                then, chan, said = IRCClient.seen[who]
                delta = time.time() - then
                seen = ('%s, %s was last seen in %s %s ago saying: %s' % (nick, who, chan, time_ago(delta), said))
                IRCClient.msg(dest, seen)
            else:
                IRCClient.msg(dest, 'I have not seen %s before.' % who)

def owner_triggers(IRCClient, dest, message):
    '''Triggers which are only triggered in PM from bot owner.'''
    trigger, sep, text = message.partition(' ')

    if trigger == '!raw':
        IRCClient.send_data(text)

    else:
        dest, sep, msg = text.partition(' ')
        if trigger == '!say':
            #!say <nick/channel> <text>
            IRCClient.msg(dest, msg)
        elif trigger == '!do':
            #!do <nick/channel> <text>
            IRCClient.action(dest, msg)
        elif trigger == '!join':
            IRCClient.join(dest)
        elif trigger == '!part':
            IRCClient.part(dest, msg)

def send_topic(IRCClient, chan):
    '''Print the topic of chan.'''
    if chan in IRCClient.topics:
        topic, by, time_ch = IRCClient.topics[chan]

        if '!' in by:
            by, user, host = self.split_netmask(by)

        if ':' not in time_ch:
            time_ch = time.ctime(int(time_ch))

        IRCClient.msg(chan, 'Topic for %s is: "%s" set by %s on %s' % (chan,
                                                            topic, by, time_ch))

def time_ago(diff):
    stime = ''
    if diff <= 60:
        return '%i %s' % (int(diff), 'second' if diff is 1 else 'seconds')

    else:
        if (diff / 604800) >= 1:
            factor = int(math.floor(diff / 604800))
            diff -= 604800 * factor
            stime = '%i %s ' % (factor, 'week' if factor is 1 else 'weeks')
        if diff > 0:
            if (diff / 86400) >= 1:
                factor = int(math.floor(diff / 86400))
                diff -= 86400 * factor
                stime += '%i %s ' % (factor, 'day' if factor is 1 else 'days')
        if diff > 0:
            if (diff / 3600) >= 1:
                factor = int(math.floor(diff / 3600))
                diff -= 3600 * factor
                stime += '%i %s ' % (factor, 'hour' if factor is 1 else 'hours')
        if diff > 0:
            if (diff / 60) >= 1:
                factor = int(math.floor(diff / 60))
                diff -= 60 * factor
                stime += '%i %s ' % (factor, 'minute' if factor is 1 else
                                     'minutes')
        if diff > 0:
            stime += '%i seconds' % int(diff)
    return stime
