#!/bin/sh
'''which' python3 > /dev/null && exec python3 "$0" "$@" || exec python "$0" "$@"
'''

#
# Copyright (c) 2018, Manfred Constapel
# This file is licensed under the terms of the MIT license.
#

#
# goto pymmw 
#

import os
import sys
import glob
import serial
import threading
import json
import argparse
import signal
import platform
import time

from lib.shell import *
from lib.probe import *
from lib.carrier import *

# ------------------------------------------------

def _init_(data, fw):
    global mss
    if len(data) > 0 and mss is None: 
        for item in fw:
            mss = __import__(item, fromlist=('',))
            if len(mss._read_(data, open(os.devnull, "w"))) > 1:
                return True
            mss = None
    return False


def _read_(prt, dat, timeout=2, handle=None):  # observe control port and call handler when firmware is recognized

    script_path = os.path.dirname(os.path.realpath(sys.argv[0]))
    
    fw = [os.path.splitext(item)[0].split(os.sep) for item in glob.glob(os.sep.join((script_path, 'mss', '*.py')))]
    fw = ['.'.join(mss[-2:]) for mss in fw]

    cnt = 0
    ext = {}

    try:
        
        if len(fw) == 0:
            raise Exception('no handlers found')
        
        t = time.time()

        data = ''

        reset = None
        
        while handle is None:
            data = prt.readline().decode('latin-1')
  
            if _init_(data, fw):  # firmware identified
                handle = data.strip()
                break
            else:
                print(data, end='', flush=True)
  
            if timeout is not None:
                if time.time() - timeout > t:
                    car = usb_discover(*FTDI_USB)
                    if len(car) > 0 and not reset:
                        reset = time.time()
                        if not ftdi_reset(*FTDI_USB):
                            raise Exception('carrier not supported')
                        t = reset
                        continue
                    raise Exception('no handler found')

        if mss is None:
            if not _init_(handle, fw):
                raise Exception('handler not supported')                

        reset = None

        while True:
            buf = mss._read_(data)
            
            if len(buf) < 2:
                if reset:  # reset detected
                    handler = os.path.splitext(mss.__file__.split(os.sep)[-1])[0]
                    print_log('handler:', handler, '-', 'configuration:', reset)
                    cnt += 1
                    file = open('{}/{}-{}.{}'.format('mss', handler, reset, 'cfg'), 'r')
                    content = load_config(file)
                    cfg = json.loads(content)
                    cfg, par = mss._conf_(cfg)
                    mss._init_(prt, dev, cfg, dat)
                    mss._proc_(cfg, par)
                    send_config(prt, cfg, mss._read_)
                    show_config(cfg)
                reset = None
            else:
                reset = buf

            data = prt.readline().decode('latin-1')
            
    except Exception as e:
        print_log(e, sys._getframe())
        os._exit(1)
            

def _input_(prt):  # accept keyboard input and forward to control port
    while not sys.stdin.closed:
        line = sys.stdin.readline()   
        if not line.startswith('%'):
            prt.write(line.encode())

# ------------------------------------------------

if __name__ == "__main__":

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    nrst = 'Windows' not in platform.system()

    try:

        parser = argparse.ArgumentParser(description='pymmw', epilog='', add_help=True, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        
        parser.add_argument('-c', '--control-port', help='serial port for control communication', required=not nrst or '-n' in sys.argv or '--no-discovery' in sys.argv)
        parser.add_argument('-d', '--data-port', help='serial port auxiliary communication', required=not nrst or '-n' in sys.argv or '--no-discovery' in sys.argv)
        parser.add_argument('-f', '--force-handler', help='force handler for data processing (disables autodetection)', required=False)
        parser.add_argument('-n', '--no-discovery', help='no discovery for USB devices (avoids pre-access to the XDS debug probe)', action='store_true')        
                
        args = parser.parse_args()

        # ---
        
        dev, prts = None, (None, None)

        nrst = nrst and not args.no_discovery
  
        if nrst:
            try:
                dev = usb_discover(*XDS_USB)
                if len(dev) == 0: raise Exception('no device detected')
         
                dev = dev[0]
                print_log(' - '.join([dev._details_[k] for k in dev._details_]))
 
                for rst in (False,):
                    try:
                        xds_test(dev, reset=rst)
                        break
                    except:
                        pass
                     
                prts = serial_discover(*XDS_USB, sid=dev._details_['serial'])
                if len(prts) != 2: raise Exception('unknown device configuration detected')
         
            except:
                nrst = False

        # ---

        if args.control_port is None: args.control_port = prts[0]
        if args.data_port is None: args.data_port = prts[1]        
        
        # ---
        
        mss = None
        
        con = serial.Serial(args.control_port, 115200, timeout=0.01)        
        if con is None: raise Exception('not able to connect to control port')

        print_log('control port: {} - data port: {}'.format(args.control_port, args.data_port))

        if args.force_handler:
            print_log('handler: {}'.format(args.force_handler))

        tusr = threading.Thread(target=_read_, args=(con, args.data_port, None if not nrst else 2, args.force_handler))
        tusr.start()

        tstd = threading.Thread(target=_input_, args=(con,), )
        tstd.start()

        # ---
        
        if nrst:
            xds_reset(dev)
            usb_free(dev)
        else:
            print('\nwaiting for reset (NRST) of the device', file=sys.stderr, flush=True)

    except Exception as e:         
        print_log(e, sys._getframe())
        os._exit(1)
