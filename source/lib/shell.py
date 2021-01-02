#
# Copyright (c) 2018, Manfred Constapel
# This file is licensed under the terms of the MIT license.
#

#
# shell and ipc
#

import os, time, sys, subprocess

from lib.helper import *

# ------------------------------------------------

def print_log(*msg):
    pre = ('i', 'w', 'e', 'm')    
    res = [pre[0], '', '', []]
    for part in msg:
        if type(part) == type(sys._getframe()):
            res[1] = os.path.splitext(os.path.basename(part.f_code.co_filename))[0]
            res[2] = part.f_code.co_name
        elif type(part) in (list, tuple):
            res[3] += part
        elif part is not None:
            if type(part) in (RuntimeError, ModuleNotFoundError, BrokenPipeError):
                res[0] = pre[1]
            elif type(part) == Exception:
                res[0] = pre[2]
            res[3].append(str(part))
        else:
            res[0] = pre[3]
    res[3] = ' '.join(res[3])
    s = '({}) {}\n'.format(res[0], ' '.join(res[1:]))
    while '  ' in s:
        s = s.replace('  ', ' ')
    sys.stderr.write(s)
    sys.stderr.flush()

# ------------------------------------------------

def load_config(f):
    content = ''
    for line in f: content += line
    for param in ('chirpCfg', 'cfarCfg', 'cfarFovCfg'):
        idx = 0
        ccfg = []
        while idx > -1:        
            idx = content.find(param, idx + 1)
            if content[idx + len(param)] != '|': ccfg.append(idx)
        ccfg = ccfg[:-1]
        idx = 0
        for i, c in enumerate(ccfg):
            idx = c + len(param) + i * 2
            content = content[:idx] + '|{}'.format(i) + content[idx:]
    return content

      
def make_config(dump, root=True):  # read data structure and put it to a string
    value = ''
    if type(dump) in (dict,):
        for key in dump:
            item = dump[key]
            if root:
                if '|' in key: key = key[:-key[::-1].index('|') - 1]  
                value += '\n{} '.format(key)
            value += make_config(item, False)
    elif type(dump) in (list, tuple,):
        value += '{} '.format(''.join([make_config(v, False) for v in dump]))
    else:
        if dump is not None:
            value += '{} '.format(dump)
    return value


def send_config(prt, cfg=None, cli=None):  # send commands to the device and handle the response
    post = ()
    if cfg is not None:
        post = ('flushCfg',) + tuple(make_config(cfg).split('\n')[1:])        
    post = ('%', 'sensorStop',) + post + ('sensorStart', )
    for cmd in post:
        while cli is not None:
            line = prt.readline()
            if len(cli(line.decode('latin-1'))) == 1:
                time.sleep(0.01)
                break
        if cfg is not None:
            print(cmd, file=sys.stderr, flush=True)
        cmd = cmd + '\n'
        cmd = bytes(cmd, 'latin-1')
        prt.write(cmd)
        if cli is None:
            time.sleep(0.25)


def show_config(cfg):  # simple print of resultant configuration
    
    info = 'Start frequency (GHz):    \t{}\n' + \
           'Slope (MHz/us):           \t{}\n' + \
           'Sampling rate (MS/s):     \t{:.2f}\n' + \
           'Sweep bandwidth (GHz):    \t{:.2f}\n' + \
           'Frame periodicity (ms):   \t{}\n' + \
           '\n' + \
           'Loops per frame:          \t{}\n' + \
           'Chirps per loop:          \t{}\n' + \
           'Samples per chirp:        \t{}\n' + \
           'Chirps per frame:         \t{}\n' + \
           'Samples per frame:        \t{}\n' + \
           'Receive antennas:         \t{}\n' + \
           '\n' + \
           'Azimuth antennas:         \t{}\n' + \
           'Elevation antennas:       \t{}\n' + \
           'Virtual antennas:         \t{}\n' + \
           'Azimuth resolution (°):   \t{:.1f}\n' + \
           '\n' + \
           'Range resolution (m):     \t{:.4f}\n' + \
           'Range bin (m):            \t{:.4f}\n' + \
           'Range depth (m):          \t{:.4f}\n' + \
           'Unambiguous range (m):    \t{:.4f}\n' + \
           'Range bins:               \t{}\n' + \
           '\n' + \
           'Doppler resolution (m/s): \t{:.4f}\n' + \
           'Maximum Doppler (m/s):    \t{:.4f}\n' + \
           'Doppler bins:             \t{}\n' + \
           ''

    info = info.format(
        
        cfg['profileCfg']['startFreq'],
        cfg['profileCfg']['freqSlope'],
        cfg['profileCfg']['sampleRate'] / 1000.0,
        bandwidth(cfg),        
        cfg['frameCfg']['periodicity'],

        cfg['frameCfg']['loops'],
        chirps_per_loop(cfg),
        samples_per_chirp(cfg),
        chirps_per_frame(cfg),
        samples_per_frame(cfg),
        num_rx_antenna(cfg),
        
        num_tx_azim_antenna(cfg),
        num_tx_elev_antenna(cfg),
        num_virtual_antenna(cfg),
        angular_resolution(cfg),
                
        range_resolution(cfg),
        range_bin(cfg),
        range_maximum(cfg),
        range_unambiguous(cfg),
        num_range_bin(cfg),
        
        doppler_resolution(cfg),
        doppler_maximum(cfg),
        num_doppler_bin(cfg),
        
    )

    print(file=sys.stderr, flush=True)
    print(info, file=sys.stderr, flush=True)

# ------------------------------------------------

def exec_app(name, args=None, path='./app/'):
   
    param = []

    if type(args) in (list,):  # fill up param with arguments
        for arg in args:
            try: param.append('{:.6f}'.format(arg))
            except: param.append('{}'.format(arg))
    
    # call either with or without arguments
    proc = subprocess.Popen([sys.executable, path + name + '.py', *param], cwd='.',
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    if type(args) not in (list,):  # check output if called without arguments
        
        try:
            out, _ = proc.communicate(timeout=2)
        except:
            proc, param = exec_app(name, [])  # it seems the process was not requesting any arguments
        
        if proc.poll() is not None:

            res = out.decode('latin-1')
            res = (arg[1:-1] for arg in (item.rstrip() for item in res.split(' ')) if len(arg) > 2 and arg[0] == '<' and arg[-1] == '>')
            
            if args is None:  # just return the arguments expected
                param = tuple(res)
                
            elif type(args) in (tuple,):  # map values from tuple items to required arguments
                cfg, par = args
                for item in res:
                    if item in globals() and callable(globals()[item]):
                        param.append(globals()[item](cfg))
                    elif par is not None and type(par) in (dict,) and item in par:
                        param.append(par[item])                    
                    else:
                        return proc, None
                return exec_app(name, param)  # recursive call with a list of values for arguments
        
        else:
            proc.kill()

    return proc, param
