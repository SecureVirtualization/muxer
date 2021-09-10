#!/usr/bin/python3
#! \file mux.py
# This file contains implementation of UART/pts muxer.
#
# \author Alexander Trofimov <molochmail@gmail.com>
#
# \copyright Copyright 2019 Alexander Trofimov. All rights reserved.
# Alexander Trofimov retain all intellectual property and proprietary rights
# in and to this software, related documentation and any modifications
# thereto. Any use, reproduction, disclosure or distribution of this software
# and related documentation without an express license agreement from
# the owner is strictly prohibited.

import serial
import sys
import pty
import os
import signal
import select
import time

tag_current = 0
tag_in_current = 0
id_names = {
        0xff : 'V8H',
        0    : 'VM0',
        1    : 'VM1',
        2    : 'VM2',
        3    : 'VM3',
        4    : 'VM4',
        5    : 'VM5',
        6    : 'VM6',
        7    : 'VM7',
        }
id_hv = {
        0xff : b'\xff',
        0    : b'\x00',
        1    : b'\x01',
        2    : b'\x02',
        3    : b'\x03',
        4    : b'\x04',
        5    : b'\x05',
        6    : b'\x06',
        7    : b'\x07',
        }
id_available = (
        0xff,
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7)
id_pts = {}
id_pts_reverse = {}
slaves = []
shutdown = False

def pts_allocate():
    global id_pts
    global id_pts_reverse
    global slaves
    for k in id_names:
        master, slave = os.openpty()
        print ('Allocating pts for ' + id_names[k] + ' file ' + os.ttyname(slave) + ' k ' + str(k))
        id_pts[k] = master
        id_pts_reverse[master] = k
        slaves.append(slave)

def pts_cleanup():
    global id_pts
    global id_pts_reverse
    global slaves
    for k in id_pts:
        os.close(id_pts[k])
    for d in slaves:
        os.close(d)
    id_pts.clear()
    id_pts_reverse.clear()
    slaves.clear()

def output(tag, string):
    global id_names
    global id_pts
    pty = id_pts[tag]
    out = (string).encode('utf-8')
    os.write(pty, out)

def spawn_tty_dispatcher(name):
    global tag_current
    global tag_in_current
    global shutdown
    global id_pts_reverse
    global id_hv

    s = serial.Serial(name, baudrate=115200, timeout = 0.1)
    if not s:
        print ('[err]: cannot open serial device ' + name)
        return
    pts_allocate()

    # create joint select list
    readers = [s]
    for k in id_pts:
        readers.append(id_pts[k])

    # at first we set vm0 to be a main input
    s.write(b'\xff')
    s.write(id_hv[tag_in_current])


    while not shutdown:
        r, _, _ = select.select(readers, [], [], 0.1)

        for d in r:
            if s == d:
                l = s.readline()
                if l:
                    # there might be multiple 0xff entries iterate through it
                    cond = True
                    while cond and len(l):
                        if 0xff in l:
                            off = l.index(0xff)
                            if off > 1:
                                output (tag_current, str(l[:off-1], 'utf-8', 'ignore'))
                            if ((off + 1) < len (l)) and (l[off+1] in id_available):
                                # filter wrong or broken tags
                                tag_current = l[off+1]
                            else:
                                cond = False
                            if (off + 2) < len (l):
                                l = l[off+2:]
                            else:
                                cond = False
                        else:
                            output (tag_current, str(l, 'utf-8', 'ignore'))
                            cond = False
                else:
                    print ('unexpected no data from serial')
            else:
                c = os.read(d, 1)
                if tag_in_current != id_pts_reverse[d]:
                    tag_in_current = id_pts_reverse[d]
                    s.write(b'\xff')
                    s.write(id_hv[tag_in_current])
                s.write(c)


name = '/dev/ttyUSB0'
if len(sys.argv) > 1:
    name = sys.argv[1]

while not shutdown:
    try:
        try:
            spawn_tty_dispatcher (name)
        except (serial.SerialException, IndexError) as e:
            print ('Got exception, pause 200 msec and retry.')
            print (e)
            # do cleanup of pts
            pts_cleanup()
            time.sleep(0.5)
    except KeyboardInterrupt:
        shutdown = True
        print ('Quitting...')
