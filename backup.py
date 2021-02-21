#!/usr/bin/env python

""" Simple way to do backups.
"""
import csv
import datetime
import json
import logging
import logging.config
import optparse
import os
from pprint import pprint
from shlex import quote
import subprocess
import sys


# https://serverfault.com/questions/470046/rsync-from-linux-host-to-fat32
PARAMS = '-rtD --modify-window=1 --size-only'

# Add (params, src, dst) 3-tuples to the BACKUPS list.
# All paths should end in a /
# ~ is expanded to the user's home directory.
BACKUPS = [
    (PARAMS, '/tmp/logs/', 'backup/logs/%w/'),
    (PARAMS, '~/zettelkasten/', 'backup/zettelkasten/%w/'),
    (PARAMS, '~/.ssh/', 'backup/.ssh/%w/'),
    (PARAMS, '~/tax/', 'backup/tax/%w/'),
]

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


def ensure_directory_exists(path, expand_user=True, file=False):
    """ Create a directory if it doesn't exists.

        Expanding '~' to the user's home directory on POSIX systems.
    """
    if expand_user:
        path = os.path.expanduser(path)

    if file:
        directory = os.path.dirname(path)
    else:
        directory = path

    if not os.path.exists(directory) and directory:
        try:
            os.makedirs(directory)
        except OSError as e:
            # A parallel process created the directory after the existence check.
            pass

    return(path)


def partitions():
    """ Return {partition: mountpoint}.
    """
    d = {}
    command = "lsblk -J"
    r = json.loads(subprocess.check_output(command, shell=True))
    for rec in r.get('blockdevices', []):
        if rec.get('type') in ['disk']:
            for child in rec.get('children', []):
                if child.get('type') in ['part']:
                    name = child.get('name')
                    mountpoint = child.get('mountpoint')
                    d[name] = mountpoint
    return d


def mount(device):
    """ udiskie-mount the device.
        https://pypi.org/project/udiskie/
    """
    command = f"udiskie-mount /dev/{device} >/dev/null 2>&1"
    subprocess.check_call(command, shell=True)


def umount(device):
    """ udiskie-umount the device.
        https://pypi.org/project/udiskie/
    """
    command = f"udiskie-umount /dev/{device} >/dev/null 2>&1"
    subprocess.check_call(command, shell=True)


def rsync(params, src, dst):
    """ Execute rsync command.
    """
    # command = "rsync {params} {src} {dst} >/dev/null 2>&1".format(params=params, src=quote(src), dst=quote(dst))
    command = "rsync {params} {src} {dst}".format(params=params, src=quote(src), dst=quote(dst))
    subprocess.check_call(command, shell=True)


if __name__ == '__main__':

    logger.info('Backup start: ' + ' '.join(sys.argv))
    parser = optparse.OptionParser()
    parser.add_option('-d',
                      '--device',
                      dest='device',
                      action='store',
                      type='string',
                      default='',
                      help='storage device (partition)')

    options, args = parser.parse_args()

    if not (options.device):
        parser.print_help()
        sys.exit()

    now = datetime.datetime.now()
    device = os.path.basename(options.device)

    # Hack.
    umount(device)

    partitions_ = partitions()
    mountpoint = partitions_.get(device)
    if mountpoint:
        logger.error(f'Device {device} ready mounted on {mountpoint}')
        sys.exit(f'Unmount {device} and try again.')
    else:
        if device not in partitions_:
            logger.error(f'Device {device} not found.')
            sys.exit(f'Is device {device} plugged in?')
        else:
            mount(device)
            partitions_ = partitions()
            mountpoint = partitions_.get(device)
            logger.info(f'Device {device} mounted on {mountpoint}')

    # Do rsync's.
    for params, source, destination in BACKUPS:
        try:
            src = os.path.expanduser(source)
            if '%' in src:
                src = now.strftime(src)

            dst = os.path.join(mountpoint, destination)
            if '%' in dst:
                dst = now.strftime(dst)

            if dst.endswith('/'):
                ensure_directory_exists(dst)
            else:
                ensure_directory_exists(dst, file=True)

            rsync(params, src, dst)
        except:
            logger.exception()

    logger.info('Backup done.')

