import os, datetime

def log(msg):
    '''
    Write a message to various logs.
    '''
    log_console(msg)
    log_file(msg)


def log_console(msg):
    '''
    Logs a message to the console with timestamp.
    '''
    now = datetime.datetime.now().strftime('%H:%M:%S')
    full_msg = '[SQUIDLogger %s] %s\n' %(now, msg)
    os.write(1, bytes(full_msg, encoding='utf-8'))


def log_file(msg):
    pass
