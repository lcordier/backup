#!/usr/bin/env python

""" Simple way to do backups.
"""
import csv
import datetime
import logging
import logging.config
import optparse
import os
from shlex import quote
import subprocess
import sys


ROOT = os.path.dirname(os.path.abspath(__file__))

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'summary',
            'stream': 'ext://sys.stdout',
        },
        'null': {
            'class': 'logging.NullHandler',
            'level': 'NOTSET',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'summary',
            'filename': os.path.join(ROOT, 'backup.log'),
            'mode': 'a',
            'maxBytes': 10485760,
            'backupCount': 5,
        },
    },
    'formatters': {
        'summary': {
            'format': '%(asctime)s [%(levelname)-8s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        }
    }
}


logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger()


def exec_(cmd, params, src, dst):
    """ Execute command.
    """
    if not dst:
        command = "{cmd} {params} {src}".format(cmd=cmd, params=params, src=quote(src))
    else:
        command = "{cmd} {params} {src} {dst}".format(cmd=cmd, params=params, src=quote(src), dst=quote(dst))
    subprocess.check_call(command, shell=True)


def rsync(cmd, params, src, dst):
    """ Execute rsync command.
    """
    # command = "rsync {params} {src} {dst} >/dev/null 2>&1".format(params=params, src=quote(src), dst=quote(dst))
    command = "rsync {params} {src} {dst}".format(params=params, src=quote(src), dst=quote(dst))
    subprocess.check_call(command, shell=True)


def fail(cmd, params, src, dst):
    """ Test the existance of dst.
    """
    if not os.path.exists(dst):
        raise FailError('{} does not exist.'.format(dst))


COMMANDS = {
    'rsync': rsync,
    'fail': fail,
}


class FailError(Exception):
    pass


if __name__ == '__main__':

    logger.info('Backup start: ' + ' '.join(sys.argv))

    parser = optparse.OptionParser()

    parser.add_option('-c',
                      '--config',
                      dest='config',
                      action='store',
                      type='string',
                      default='',
                      help='backup config file')

    options, args = parser.parse_args()

    if not (options.config):
        parser.print_help()
        sys.exit()

    now = datetime.datetime.now()

    config = open(options.config, 'r')
    reader = csv.reader(config)
    header = next(reader)

    for idx, row in enumerate(reader, 2):
        cmd, params, src, dst = [field.strip() for field in row]
        try:
            if '%' in src:
                src = now.strftime(src)

            if '%' in dst:
                dst = now.strftime(dst)

            func = COMMANDS.get(cmd.lower(), exec_)
            if func:
                func(cmd, params, src, dst)
            else:
                logger.error('Unknown command, row={}: {}'.format(idx, ','.join(row)))
        except FailError as e:
            logger.error(e)
            break
        except:
            logger.exception('row={}: {}'.format(idx, ','.join(row)))

