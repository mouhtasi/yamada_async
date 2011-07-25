import time

class Logger():

    def __init__(self, filename):
        self.filename = filename
        self.f = self.open_log(filename)

    def open_log(self, filename):
        f = open(filename, 'a+')
        f.write('%s Log opened.\n' % self.timestamp())
        f.flush()
        return f

    def close_log(self, reason):
        self.log('Log closed - %s\n' % reason)
        self.f.close()

    def log(self, message):
        self.f.write('%s %s\n' % (self.timestamp(), message))

    def timestamp(self):
        return time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime(time.time()))
