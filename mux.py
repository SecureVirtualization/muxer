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

tag_current = 0xff
id_names = {
        0xff : '[V8H]: ',
        0    : '[VM0]: ',
        1    : '[VM1]: ',
        2    : '[VM2]: ',
        3    : '[VM3]: '
        }
id_pts = {}

def allocate_pts():
    global id_pts
    for k in id_names:
        master, slave = os.openpty()
        print ('Allocating pts for id ' + str(k))
        print (os.ttyname(master))
        print (os.ttyname(slave))
        id_pts[k] = master

def output(tag, string):
    global id_names
    global id_pts
    pty = id_pts[tag]
    out = (string).encode('utf-8')
    os.write(pty, out)

def spawn_tty_dispatcher(name):
    global tag_current
    s = serial.Serial(name)
    if not s:
        print ('[err]: cannot open serial device ' + name)
        return
    allocate_pts()
    while True:
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
            break

name = '/dev/ttyUSB0'
if len(sys.argv) > 1:
    name = sys.argv[1]
spawn_tty_dispatcher (name)
