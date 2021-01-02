#
# Copyright (c) 2019, Manfred Constapel
# This file is licensed under the terms of the MIT license.
#

#
# usb and xds110 debugger support
#

import sys, time, array

from lib.utility import *
from lib.shell import *

# ------------------------------------------------

VID, PID = 0x0451, 0xbef3  # XDS110

# ------------------------------------------------

try:
    import usb
    import serial.tools.list_ports
except ImportError as e:
    print_log(e, sys._getframe())

# ------------------------------------------------

def usb_discover(vid=VID, pid=PID, man=None, pro=None, sid=None):
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

def serial_discover(vid=VID, pid=PID, sid=None):
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

# ------------------------------------------------

def xds_reset(dev, delay=50):
    #_ = {0:'CDC Communication',
    #     1:'CDC Data', 2:'Vendor Specific', 3:'CDC Communication',
    #     4:'CDC Data', 5:'Human Interface Device', 6:'Vendor Specific'}
    ep = usb_point(dev, 2, 2)
    if ep is None: return False
    for v in ('00', '01'):
        ep.write(hex2dec('{} {} {} {}'.format('2a', '02', '00', '0e {}'.format(v))))
        time.sleep(delay / 1000)
    return True

# ------------------------------------------

__scan_test__ = (

    '2a 01 00 01',
    '2a 01 00 03',                   '2a 05 00 04 00 00 00 00',    
    '2a 01 00 06', '2a 02 00 05 00', '2a 05 00 07 88 13 00 00',
                   '2a 02 00 05 01', '2a 05 00 07 a0 86 01 00',
                                     '2a 05 00 2b 01 00 00 00',    
    '2a 01 00 06', '2a 02 00 05 00', '2a 05 00 07 88 13 00 00',
                   '2a 02 00 05 01', '2a 05 00 07 a0 86 01 00', '2a 09 00 09 01 00 00 00 01 00 00 00',
    
    '2a 01 00 1a',
    '2a 01 00 2f',
    '2a 01 00 02',
    
    '2a 01 00 01',
    '2a 01 00 03',                   '2a 05 00 04 00 00 00 00',
    '2a 01 00 06', '2a 02 00 05 00', '2a 05 00 07 88 13 00 00',
                   '2a 02 00 05 01', '2a 05 00 07 a0 86 01 00',
                                     '2a 05 00 2b 01 00 00 00',

    '2a 10 00 0a 00 08 04 01 06 01 00 00 00 00 00 00 01 00 01',
    '2a 13 01 0c 00 08 04 01 06 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('ff ff ff ff',)*4*16)),
    '2a 13 01 0c 00 08 04 01 06 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('00 00 00 00',)*4*16)),
    '2a 13 01 0c 00 08 04 01 06 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('00 00 00 00',)*4*16)),
    '2a 13 01 0c 00 08 04 01 06 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('ff ff ff ff',)*4*16)),
 
    '2a 10 00 0a 00 08 03 01 05 01 00 00 00 00 00 00 01 00 01',
    '2a 13 01 0c 00 08 03 01 05 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('ff ff ff ff',)*4*16)),
    '2a 13 01 0c 00 08 03 01 05 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('00 00 00 00',)*4*16)),
    '2a 13 01 0c 00 08 03 01 05 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('00 00 00 00',)*4*16)),
    '2a 13 01 0c 00 08 03 01 05 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('ff ff ff ff',)*4*16)),

    '2a 15 00 0b 20 00 04 01 06 01 00 00 00 00 00 00 01 00 04 00 ff ff ff ff',
    '2a 13 01 0c 00 08 04 01 06 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('ff ff ff ff',)*4*16)),
    '2a 15 00 0b 20 00 04 01 06 01 00 00 00 00 00 00 01 00 04 00 00 00 00 00',
    '2a 13 01 0c 00 08 04 01 06 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('00 00 00 00',)*4*16)),
    '2a 15 00 0b 20 00 04 01 06 01 00 00 00 00 00 00 01 00 04 00 e2 e0 03 fe',
    '2a 13 01 0c 00 08 04 01 06 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('e2 e0 03 fe',)*4*16)),
    '2a 15 00 0b 20 00 04 01 06 01 00 00 00 00 00 00 01 00 04 00 1d 1f fc 01',
    '2a 13 01 0c 00 08 04 01 06 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('1d 1f fc 01',)*4*16)),
    '2a 15 00 0b 20 00 04 01 06 01 00 00 00 00 00 00 01 00 04 00 aa cc 33 55',
    '2a 13 01 0c 00 08 04 01 06 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('aa cc 33 55',)*4*16)),
    '2a 15 00 0b 20 00 04 01 06 01 00 00 00 00 00 00 01 00 04 00 55 33 cc aa',
    '2a 13 01 0c 00 08 04 01 06 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('55 33 cc aa',)*4*16)),

    '2a 10 00 0a 00 08 04 01 06 01 00 00 00 00 00 00 01 00 01',
    '2a 01 00 08',
    '2a 09 00 09 05 00 00 00 02 00 00 00',

    '2a 15 00 0b 20 00 03 01 05 01 00 00 00 00 00 00 01 00 04 00 ff ff ff ff',
    '2a 13 01 0c 00 08 03 01 05 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('ff ff ff ff',)*4*16)),
    '2a 15 00 0b 20 00 03 01 05 01 00 00 00 00 00 00 01 00 04 00 00 00 00 00',
    '2a 13 01 0c 00 08 03 01 05 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('00 00 00 00',)*4*16)),
    '2a 15 00 0b 20 00 03 01 05 01 00 00 00 00 00 00 01 00 04 00 e2 e0 03 fe',
    '2a 13 01 0c 00 08 03 01 05 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('e2 e0 03 fe',)*4*16)),
    '2a 15 00 0b 20 00 03 01 05 01 00 00 00 00 00 00 01 00 04 00 1d 1f fc 01',
    '2a 13 01 0c 00 08 03 01 05 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('1d 1f fc 01',)*4*16)),
    '2a 15 00 0b 20 00 03 01 05 01 00 00 00 00 00 00 01 00 04 00 aa cc 33 55',
    '2a 13 01 0c 00 08 03 01 05 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('aa cc 33 55',)*4*16)),
    '2a 15 00 0b 20 00 03 01 05 01 00 00 00 00 00 00 01 00 04 00 55 33 cc aa',
    '2a 13 01 0c 00 08 03 01 05 01 00 00 00 00 00 00 01 00 00 01 00 01 {}'.format(' '.join(('55 33 cc aa',)*4*16)),

    '2a 01 00 1a',
    '2a 01 00 2f',
    '2a 01 00 02'
)

def xds_test(dev, reset=True):
   
    if reset:
        xds_reset(dev)
    
    ep2o = usb_point(dev, 2, 2)
    ep2i = usb_point(dev, 2, 3)

    _ = dev.read(ep2i.bEndpointAddress, 1024)

    def send(epo, msg, epi=None):
        _ = epo.write(hex2dec(msg))
        if epi is not None:
            buf = dev.read(epi.bEndpointAddress, 1024)
            return buf
        return None

    def collect(v):
        res = send(ep2o, v, ep2i)
        if res is not None:
            if len(res) > 21:
                res = set(res[8:])
                if len(res) % 3 != 1:  # super-lazy check
                    return False
        return True
        
    for entry in __scan_test__:
        if not collect(entry):
            raise Exception('integrity scan-test on the JTAG DR/IR has failed')
