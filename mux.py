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

tag_current = 0xff
tag_in_current = 0
id_names = {
        0xff : 'V8H',
        0    : 'VM0',
        1    : 'VM1',
        2    : 'VM2',
        3    : 'VM3'
        }
id_pts = {}
shutdown = False

def allocate_pts():
    global id_pts
    for k in id_names:
        master, slave = os.openpty()
        print ('Allocating pts for ' + id_names[k] + ' file ' + os.ttyname(slave))
        id_pts[k] = master

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
    s = serial.Serial(name)
    if not s:
        print ('[err]: cannot open serial device ' + name)
        return
    allocate_pts()
    while not shutdown:
        readers = [s, id_pts[0xff], id_pts[0]]
        r, _, _ = select.select(readers, [], [], 0.5)
        if len(r) == 0:
            continue

        if s in r:
            l = s.readline()
            if l:
                if 0xff in l:
                    off = l.index(0xff)
                    if off > 1:
                        output (tag_current, str(l[:off-1], 'utf-8'))
                    tag_current = l[off+1]
                    output (tag_current, str(l[off+2:], 'utf-8'))
                else:
                    output (tag_current, str(l, 'utf-8'))
            else:
                print ('unexpected no data from serial')
        if id_pts[0xff] in r:
            if tag_in_current != 0xff:
                tag_in_current = 0xff
                s.write(b'\xff')
                s.write(b'\xff')
            s.write(os.read(id_pts[0xff], 1))
#            print ('input for ' + id_names[0xff] + str(os.read(id_pts[0xff], 0xff), 'utf-8'))
        if id_pts[0] in r:
            print ('input for ' + id_names[0] + str(os.read(id_pts[0], 0xff), 'utf-8'))


name = '/dev/ttyUSB0'
if len(sys.argv) > 1:
    name = sys.argv[1]

while not shutdown:
    try:
        try:
            spawn_tty_dispatcher (name)
        except serial.SerialException:
            print ('Got exception from serial, pause 5 sec and retry.')
            time.sleep(5)
    except KeyboardInterrupt:
        shutdown = True
        print ('Quitting...')
