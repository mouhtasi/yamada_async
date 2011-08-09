import logger
import yaml
import sys
import irc

if __name__ == '__main__':
    from asyncore import loop
    if len(sys.argv)> 1:
        arg = sys.argv[1]
        if arg == '-h' or arg == '--help':
            print 'Usage: python yamada_async.py <config>'
            sys.exit(0)
        else:
            f = arg
    else:
        f = 'config.yaml'

    conf = open(f, 'r')
    config = yaml.load(conf)
    conf.close()
    owner = config['owner']

    if 'logfile' in config:
        logfile = config['logfile']
    else:
        logfile = '%s.log' % config['nick']

    log = logger.Logger(logfile)

    client = irc.IRCClient(config['host'], config['port'], config['nick'],
                           config['username'], '' if (config['nick_pass'] is None)
                           else config['nick_pass'], config['channels'], log)

    try:
        loop(timeout=1)
    except KeyboardInterrupt:
        client.save_seen()
        log.close_log('Terminated by user.')
        print 'Terminated by user.'
    except:
        log.close_log('Fatal error.')
        print 'Terminated due to fatal error.'
