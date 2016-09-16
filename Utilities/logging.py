import os, datetime

def log(msg):
    '''
    Logs a message to the console with timestamp.
    '''
    now = datetime.datetime.now().strftime('%H:%m:%S')
    full_msg = '[SQUIDLogger %s] %s\n' %(now, msg)
    os.write(1, bytes(full_msg, encoding='utf-8'))
