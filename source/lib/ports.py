#
# Copyright (c) 2019, Manfred Constapel
# This file is licensed under the terms of the MIT license.
#

#
# usb and serial support
#

import sys
import time
import array

from lib.utility import *
from lib.shell import *

# ------------------------------------------

try:

    import usb
    import serial.tools.list_ports

except ImportError as e:
    print_log(e, sys._getframe())

# ------------------------------------------

def usb_discover(vid, pid, man=None, pro=None, sid=None):
    found = []
    try:
        devs = usb.core.find(find_all=True)
        for dev in devs:
            if dev.idVendor == vid and dev.idProduct == pid:
                m = usb.util.get_string(dev, dev.iManufacturer)
                p = usb.util.get_string(dev, dev.iProduct)
                s = usb.util.get_string(dev, dev.iSerialNumber)
                if (man is None or m is not None and m.startswith(man)) and \
                    (pro is None or p is not None and p.startswith(pro)) and \
                     (sid is None or s is not None and s.startswith(sid)):
                    dev._detached_ = []
                    dev._details_ = {'serial': s, 'manufacturer': m, 'product': p}
                    found.append(dev)
    except Exception as e:
        print_log(e, sys._getframe())
    return found


def usb_point(dev, num, end):
    ept = (usb.util.ENDPOINT_IN, usb.util.ENDPOINT_OUT)
    cfg = dev.get_active_configuration()
    intf = cfg[(num, 0)]
    ep = usb.util.find_descriptor(intf,
        custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == ept[int(end % 2 == 0)])
    return ep


def usb_free(dev):
    usb.util.dispose_resources(dev)    
    for ifn in dev._detached_:
        usb.util.release_interface(dev, ifn)
        try: dev.attach_kernel_driver(ifn)
        except: pass

# ------------------------------------------

def serial_discover(vid, pid, sid=None):
    found = []
    if type(sid) == str and len(sid) == 0: sid = None        
    try:
        ports = serial.tools.list_ports.comports()
        for port in sorted(ports):
            if port.vid != vid or port.pid != pid or port.serial_number != sid: continue
            found.append(port.device)
    except Exception as e:
        print_log(e, sys._getframe())
    return found
