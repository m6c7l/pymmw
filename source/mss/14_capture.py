#
# Copyright (c) 2019, Manfred Constapel
# This file is licensed under the terms of the MIT license.
#

#
# TI IWR1443 ES2.0 EVM @ capture demo of SDK 1.1.0.2
#

import os, time, sys, threading, serial

from lib.probe import *
from lib.shell import *
from lib.helper import *
from lib.utility import *

# ------------------------------------------------

_meta_ = {
    'mss': 'Capture Demo',
    'dev': ('xWR14xx',),
    'ver': ('01.01.00.02', ),
    'cli': 'CaptureDemo:/>',
    'ccs': os.environ.get('CCS_PATH'),  # full path to CCS for tiflash.memory_read()
    'dbg': 'XDS110',
    'mem': 0x40000,
    'typ': 'IWR1443',
    'add': 0x51020000,
    'app': [
        'dft_if_signal'
    ]
}

# ------------------------------------------------

try:
    import tiflash
except ImportError as e:
    print_log(e, sys._getframe())

# ------------------------------------------------

apps = {}

verbose = False

# ------------------------------------------------

def _read_(dat, target=sys.stdout):
    target.write(dat)
    target.flush()
    for ver in _meta_['ver']:
        for dev in _meta_['dev']:
            if all((tag in dat for tag in (dev, _meta_['mss'], ver))):
                return dev  # reset detected
    if _meta_['cli'] in dat: return (None,)  # cli ready
    return ()  # unknown state


def _init_(prt, dev, cfg, dat=None):
    if dev is not None:
        try:
            l3_size = _meta_['mem']
            ccs = _meta_['ccs']
            con = tiflash.get_connections(ccs)
            con = [c for c in con if _meta_['dbg'] in c]
            if len(con) > 0:
                con = con[0]
                frame_values = cfg['profileCfg']['adcSamples'] * num_rx_antenna(cfg) * chirps_per_frame(cfg) 
                value_size = 2 + 2
                count = cfg['frameCfg']['frames']                
                frame_size = frame_values * value_size
                if count == 0:
                    count = max(1, l3_size // frame_size)
                if frame_size * count > l3_size:
                    raise Exception('frame size ({}) exceeds buffer size ({})'.format(frame_size, l3_size))
                tmem = threading.Thread(
                    target=_data_,
                    args=(con, dev._details_['serial'], value_size, frame_values, count, prt, cfg['frameCfg']['frames'] == 0))
                tmem.start()
        except Exception as e:
            print_log(e, sys._getframe())


def _conf_(cfg):
    
    global verbose

    c = dict(cfg)
    p = {'rangebias': float('nan')}
        
    if '_comment_' in c:
        c.pop('_comment_', None)  # remove entry        
    
    if '_settings_' in c:
        
        rx_ant = int(c['_settings_']['rxAntennas'])
        tx_ant = int(c['_settings_']['txAntennas'])
        
        # common
        if c['channelCfg']['rxMask'] is None:
            c['channelCfg']['rxMask'] = 2**rx_ant - 1

        if c['channelCfg']['txMask'] is None:
            n = tx_ant
            if n == 1: n = 0
            else: n = 2 * n
            c['channelCfg']['txMask'] = 1 + n
            
        # cli output
        if 'verbose' in c['_settings_'] and c['_settings_']['verbose'] is not None:
            verbose = c['_settings_']['verbose']
                
        p['range_bias'] = c['_settings_']['rangeBias']
        
        c.pop('_settings_', None)  # remove entry
                
    return c, p


def _proc_(cfg, par, err={1: 'miss', 2: 'exec', 3: 'plot'}):
    global apps
    for _, app in apps.items(): app.kill()
    apps.clear()
    for app in _meta_['app']:
        if type(app) not in (list, tuple): app = (app,)             
        for item in app:
            if item not in apps:
                apps[item], values = exec_app(item, (cfg, par, ))
                if values is None: values = []
                code = apps[item].poll()
                if code is None:
                    print_log(item, values)
                else:
                    print_log(item, values, RuntimeError(err[code]))


def _pipe_(dat):
    for tag in apps:
        if apps[tag] is None: continue
        try:
            apps[tag].stdin.write(str.encode(dat + '\n'))
            apps[tag].stdin.flush()
        except Exception as e:
            print_log(e, sys._getframe(), tag)
            apps[tag].kill()
            apps[tag] = None


def _grab_(tag):
    pass

# ------------------------------------------------

def _data_(con, sn, sval, fval, cnt, prt, infinite=True, width=16):        
    
    time.sleep(1)
    
    active = True
    
    while active:

        try:

            print_log('read memory: address={}, bytes={}, frames={}'.format(hex(_meta_['add']), sval * fval * cnt, cnt), sys._getframe())
            
            buf = tiflash.memory_read(
                address=_meta_['add'],
                num_bytes=sval * fval * cnt,
                ccs=_meta_['ccs'],
                serno=sn,
                connection=con,
                fresh=True,
                devicetype=_meta_['typ'])

        except Exception as e:
            print_log(e, sys._getframe())
            break

        buffer = []

        tmp = dec2hex(buf)
        frames = split(tmp, sval * fval * 2)  # two chars per byte
        for frame in frames:
            buffer.append('')
            tmp = split(frame, width * sval)
            for line in tmp:
                buffer.append(' '.join(split(line, sval)))

        chunk = '\n'.join(buffer)
        _pipe_(chunk)

        if verbose:
            print(chunk, file=sys.stdout, flush=True)

        if infinite:
            send_config(prt, None, None)
            time.sleep(0.5)
            
        active = infinite
