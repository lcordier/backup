#!/usr/bin/env python

""" Simple way to do /library/ backups.
"""
import optparse
import os
import json
from shlex import quote
import subprocess
import sys


# https://serverfault.com/questions/470046/rsync-from-linux-host-to-fat32
PARAMS = '-rtD --modify-window=1 --size-only'


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


def mount(device, mountpoint):
    """ Mount the device.
    """
    command = f"sudo mount /dev/{device} {mountpoint} >/dev/null 2>&1"
    subprocess.check_call(command, shell=True)


def umount(device):
    """ Umount the device.
    """
    command = f"sudo umount /dev/{device} >/dev/null 2>&1"
    subprocess.check_call(command, shell=True)


def rsync(params, src, dst):
    """ Execute rsync command.
    """
    # command = "rsync {params} {src} {dst} >/dev/null 2>&1".format(params=params, src=quote(src), dst=quote(dst))
    command = "sudo rsync {params} {src} {dst}".format(params=params, src=quote(src), dst=quote(dst))
    subprocess.check_call(command, shell=True)


if __name__ == '__main__':

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

    device = os.path.basename(options.device)
    partitions_ = partitions()
    mountpoint = partitions_.get(device)
    if mountpoint:
        sys.exit(f'Unmount {device} and try again.')
    else:
        if device not in partitions_:
            sys.exit(f'Is device {device} plugged in?')
        else:
            mount(device, '/mnt/')
            partitions_ = partitions()
            mountpoint = partitions_.get(device)

    rsync('-av', '/library/', '/mnt/library/')
    umount(device)

