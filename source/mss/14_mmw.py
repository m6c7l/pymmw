#
# Copyright (c) 2018, Manfred Constapel
# This file is licensed under the terms of the MIT license.
#

#
# TI IWR1443 ES2.0 EVM @ mmWave SDK demo of SDK 1.2.0.5
# TI IWR1443 ES3.0 EVM @ mmWave SDK demo of SDK 2.1.0.4
#

import sys, json, serial, threading

from lib.shell import *
from lib.helper import *
from lib.utility import *

# ------------------------------------------------

_meta_ = {
    'mss': 'MMW Demo',
    'dev': ('xWR14xx',),
    'ver': ('01.02.00.05', '02.01.00.04',),
    'cli': 'mmwDemo:/>',
    'seq': b'\x02\x01\x04\x03\x06\x05\x08\x07',
    'blk': 32,
    'aux': 921600,
    'ant': (4, 3),
    'app': {
        'rangeProfile':        ('plot_range_profile', 'capture_range_profile'),
        'noiseProfile':        ('plot_range_profile', ), 
        'detectedObjects':     ('plot_detected_objects', 'simple_cfar_clustering'),
        'rangeAzimuthHeatMap': ('plot_range_azimuth_heat_map', ),
        'rangeDopplerHeatMap': ('plot_range_doppler_heat_map', )
    }
}

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


def _init_(prt, dev, cfg, dat):
    aux = serial.Serial(dat, _meta_['aux'], timeout=0.01)
    taux = threading.Thread(target=_data_, args=(aux,))
    taux.start()
        

def _conf_(cfg):
    
    global verbose     

    c = dict(cfg)
    p = {'loglin': float('nan'), 'fftcomp': float('nan'), 'rangebias': float('nan')}
    
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

        if c['channelCfg']['cascading'] is None:
            c['channelCfg']['cascading'] = 0  # always 0

        # range bias for post-processing
        if 'rangeBias' not in c['_settings_'] or c['_settings_']['rangeBias'] is None:
            c['_settings_']['rangeBias'] = 0
        
        # range bias for pre-processing
        if 'compRangeBiasAndRxChanPhase' in c:
            
            if c['compRangeBiasAndRxChanPhase']['rangeBias'] is None:
                c['compRangeBiasAndRxChanPhase']['rangeBias'] = c['_settings_']['rangeBias']
            
            if c['compRangeBiasAndRxChanPhase']['phaseBias'] is None or \
                type(c['compRangeBiasAndRxChanPhase']['phaseBias']) == list and \
                 len(c['compRangeBiasAndRxChanPhase']['phaseBias']) == 0:
                 c['compRangeBiasAndRxChanPhase']['phaseBias'] = [1, 0] * _meta_['ant'][0] * _meta_['ant'][1]

        # cli output
        if 'verbose' in c['_settings_'] and c['_settings_']['verbose'] is not None:
            verbose = c['_settings_']['verbose']
                       
        if c['dfeDataOutputMode']['type'] is None:
            c['dfeDataOutputMode']['type'] = 1  # legacy (no subframes)

        if c['adcCfg']['adcBits'] is None:
            c['adcCfg']['adcBits'] = 2  # 16 bit

        log_lin_scale = 1.0 / 512
        if num_tx_elev_antenna(c) == 1: log_lin_scale = log_lin_scale * 4.0 / 3  # MMWSDK-439

        fft_scale_comp_1d = fft_doppler_scale_compensation(32, num_range_bin(c))
        fft_scale_comp_2d = 1;                
        fft_scale_comp = fft_scale_comp_2d * fft_scale_comp_1d                
        
        p['log_lin'], p['fft_comp'], p['range_bias'] = log_lin_scale, fft_scale_comp, c['_settings_']['rangeBias']        
        
        c.pop('_settings_', None)  # remove entry
                
    return c, p


def _proc_(cfg, par, err={1: 'miss', 2: 'exec', 3: 'plot'}):
    global apps
    for _, app in apps.items(): app.kill()
    apps.clear()
    for cmd, app in _meta_['app'].items():
        if type(app) not in (list, tuple): app = (app,)             
        for item in app:
            if cmd in cfg['guiMonitor'] and cfg['guiMonitor'][cmd] == 1 and item is not None:
                if item not in apps:
                    apps[item], values = exec_app(item, (cfg, par, ))
                    if values is None: values = []
                    code = apps[item].poll()
                    if code is None:
                        print_log(item, values)
                        tapp = threading.Thread(target=_grab_, args=(item,))
                        tapp.start()
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
    try:
        while True:
            line = apps[tag].stderr.readline()
            if line:
                line = line.decode('latin-1')
                print_log(None, tag, line.strip())
    except:
        pass    

# ------------------------------------------------

def _data_(prt):  # observe auxiliary port and process incoming data
    
    if not prt.timeout:
        raise TypeError('no timeout for serial port provided')

    input, output, sync, size = {'buffer': b''}, {}, False, _meta_['blk']

    while True:
        try:
            
            data = prt.read(size)
            input['buffer'] += data
            
            if data[:len(_meta_['seq'])] == _meta_['seq']:  # check for magic sequence
                
                if len(output) > 0:
                    plain = json.dumps(output)
                    _pipe_(plain)
                    if verbose:
                        print(plain, file=sys.stdout, flush=True)  # print output to stdout
                 
                input['buffer'] = data
                input['blocks'] = -1
                input['address'] = 0
                input['values'] = 0
                input['other'] = {}
 
                output = {}                
 
                sync = True  # very first frame in the stream was seen
                
            if sync:
                flen = 0
                while flen < len(input['buffer']):  # keep things finite
                    flen = len(input['buffer'])
                    aux_buffer(input, output)  # do processing of captured bytes

        except serial.serialutil.SerialException:
            return  # leave thread

        except Exception as e:
            print_log(e, sys._getframe())

# ------------------------------------------------
            
def aux_buffer(input, output, head=36, indices={
        1: 'detected_points', 2: 'range_profile', 3: 'noise_profile',
        4: 'azimuth_static', 5: 'range_doppler', 6: 'stats', 7: 'side_info'}):

    def aux_head(dat, n=head):
        m =        dat[ 0: 8]
        v = intify(dat[ 8:12], 10)
        l = intify(dat[12:16])
        d = intify(dat[16:20], 10)
        f = intify(dat[20:24])
        t = intify(dat[24:28])
        o = intify(dat[28:32])
        s = intify(dat[32: n])
        return n, v, l, d, f, t, o, s
    
    
    def aux_struct(dat, n=8):
        t = intify(dat[ 0: 4])
        l = intify(dat[ 4: n])
        return n, t, l // 2
    
    
    def aux_descriptor(dat, n=4):  # descriptor for detected points/objects
        o = intify(dat[ 0: 2])
        q = intify(dat[ 2: n])
        return n, o, q
    
    
    def aux_object(dat, oth, n=12):  # detected points/objects 
        ri = intify(dat[ 0: 2])  # range index
        di = intify(dat[ 2: 4])  # Doppler index
        if di > 32767: di -= 65536
        di = -di                 # circular shifted fft bins
        p = intify(dat[ 4: 6])   # Doppler peak value
        x = intify(dat[ 6: 8])
        y = intify(dat[ 8:10])
        z = intify(dat[10: n])
        if x > 32767: x -= 65536
        if y > 32767: y -= 65536
        if z > 32767: z -= 65536
        qfrac = 0
        if 'qfrac' in oth: qfrac = oth['qfrac']  # q-notation is used
        x = q_to_dec(x, qfrac)
        y = q_to_dec(y, qfrac)
        z = q_to_dec(z, qfrac)
        return n, ri, di, p, x, y, z
    
    
    def aux_profile(dat, n=2):  # value of range or noise profile
        v = intify(dat[ 0: n])
        return n, v
    
    
    def aux_heatmap(dat, sgn, n=2):  # value for heatmaps
        v = intify(dat[ 0: n])
        if sgn and v > 32767: v -= 65536
        return n, v
    
    
    def aux_info(dat, n=24):  # performance measures and statistical data
        ifpt = intify(dat[ 0: 4])
        tot  = intify(dat[ 4: 8])
        ifpm = intify(dat[ 8:12])
        icpm = intify(dat[12:16])
        afpl = intify(dat[16:20])
        ifpl = intify(dat[20: n])
        return n, ifpt, tot, ifpm, icpm, afpl, ifpl

    # ----------
    
    buffer, blocks, address, values, other = \
        input['buffer'], input['blocks'], input['address'], input['values'], input['other']


    def progress(n, block, value):
        nonlocal buffer, values, address
        buffer = buffer[n:]
        values -= 1
        if values == 0: address = 0
        try:
            output[block].append(value)
        except:
            try:
                output[block][value[0]] = value[1]
            except:
                output[block] = value

    # ----------

    # 6) statistics (raw values)
    if address == 6 and len(buffer) >= 24 and values > 0:
        n, ifpt, tot, ifpm, icpm, afpl, ifpl = aux_info(buffer)
        progress(n, indices[address], {
            'interframe_processing': ifpt,
            'transmit_output': tot,
            'processing_margin': {
                'interframe': ifpm,
                'interchirp': icpm},
            'cpu_load': {
                'active_frame': afpl,
                'interframe': ifpl}
        })
    
    # 5) range-doppler heatmap: entire, 2D, log mag range/Doppler array
    while address == 5 and len(buffer) >= 2 and values > 0:
        n, v = aux_heatmap(buffer, False)
        progress(n, indices[address], v)

    # 4) range-azimuth heatmap: azimuth data from the radar cube matrix
    while address == 4 and len(buffer) >= 2 and values > 0: 
        n, v = aux_heatmap(buffer, True)
        progress(n, indices[address], v)
            
    # 3) 1D array of data considered “noise”
    while address == 3 and len(buffer) >= 2 and values > 0:
        n, v = aux_profile(buffer)
        progress(n, indices[address], q_to_db(v))

    # 2) 1D array of log mag range ffts – i.e. the first column of the log mag range-Doppler matrix
    while address == 2 and len(buffer) >= 2 and values > 0:
        n, v = aux_profile(buffer)
        progress(n, indices[address], q_to_db(v))
    
    # 1b) object detection
    while address == 1 and len(buffer) >= 12 and values > 0:
        n, r, d, p, x, y, z = aux_object(buffer, other)
        progress(n, indices[address], ('{},{}'.format(r, d), {'v': p, 'x': x, 'y': y, 'z': z}))

    # ----------
    
    # 1a) object detection descriptor
    if address == 1 and len(buffer) >= 4 and values == 0:
        n, o, q = aux_descriptor(buffer)
        buffer = buffer[n:]
        values = o
        other['qfrac'] = q
   
    # 0b) segment
    if address == 0 and len(buffer) >= 8 and blocks > 0:
        n, address, values = aux_struct(buffer)
        buffer = buffer[n:]        
        if address == 1: values = 0
        blocks -= 1
        if   address in (1, ):
            output[indices[address]] = {}
        elif address in (2, 3, 4, 5, ):
            output[indices[address]] = []
        elif address in (6, ):
            output[indices[address]] = None

    # 0a) header
    if address == 0 and len(buffer) >= head and blocks == -1:
        n, v, l, d, f, t, o, s = aux_head(buffer)
        buffer = buffer[n:]
        blocks = s
        output['header'] = {'version': v, 'length': l, 'platform': d, 'number': f, 'time': t, 'objects': o, 'blocks': s}
    
    # ----------
    
    input['buffer'] = buffer
    input['blocks'] = blocks
    input['address'] = address
    input['values'] = values
    input['other'] = other
